# admin/dashboard.py

import json
from decimal import Decimal
from datetime import timedelta

from django.db.models import Count, Case, When, IntegerField, Sum, F, Value, DecimalField
from django.db.models.functions import TruncMonth, TruncYear, Coalesce
from django.utils import timezone
from django.core.exceptions import FieldDoesNotExist

from Users.models.users_models import CustomUser
from Funds.models.funds_models import FundRaising, Donor


def _today_bounds():
    now = timezone.localtime(timezone.now())
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _this_month_bounds():
    now = timezone.localtime(timezone.now())
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return start, next_month


def _this_year_bounds():
    now = timezone.localtime(timezone.now())
    start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, start.replace(year=start.year + 1)


def _users_daily_series_last_n_days(n_days: int = 90):
    today = timezone.localdate()
    start = today - timedelta(days=n_days - 1)

    rows = (
        CustomUser.objects
        .filter(date_joined__gte=start, date_joined__lte=today)
        .values("date_joined")
        .annotate(value=Count("id"))
    )
    by_day = {r["date_joined"]: int(r["value"]) for r in rows}

    labels, values = [], []
    d = start
    while d <= today:
        labels.append(d.strftime("%Y-%m-%d"))
        values.append(by_day.get(d, 0))
        d += timedelta(days=1)

    return {"labels": labels, "values": values}


def _users_monthly_series_last_n_months(n_months: int = 12):
    today = timezone.localdate()
    current = today.replace(day=1)

    months = []
    for _ in range(n_months):
        months.append(current)
        if current.month == 1:
            current = current.replace(year=current.year - 1, month=12)
        else:
            current = current.replace(month=current.month - 1)
    months.reverse()

    rows = (
        CustomUser.objects
        .filter(date_joined__gte=months[0], date_joined__lte=today)
        .annotate(bucket=TruncMonth("date_joined"))
        .values("bucket")
        .annotate(value=Count("id"))
    )
    by_month = {r["bucket"]: int(r["value"]) for r in rows}

    labels, values = [], []
    for m in months:
        labels.append(m.strftime("%Y-%m"))
        values.append(by_month.get(m, 0))

    return {"labels": labels, "values": values}


def _users_yearly_series_last_n_years(n_years: int = 5):
    today = timezone.localdate()
    start_year = today.year - (n_years - 1)

    rows = (
        CustomUser.objects
        .filter(date_joined__year__gte=start_year)
        .annotate(bucket=TruncYear("date_joined"))
        .values("bucket")
        .annotate(value=Count("id"))
    )

    by_year = {}
    for r in rows:
        b = r["bucket"]
        y = getattr(b, "year", None)
        if y is not None:
            by_year[int(y)] = int(r["value"])

    labels, values = [], []
    for y in range(start_year, today.year + 1):
        labels.append(str(y))
        values.append(by_year.get(y, 0))

    return {"labels": labels, "values": values}


def _pick_goal_field():
    # ✅ اولویت با total_amount چون مبنای Remaining همونه
    candidates = [
        "total_amount",
        "target_amount", "goal_amount", "target_donation", "goal_donation",
        "target", "goal", "amount_goal", "total_goal",
    ]
    for name in candidates:
        try:
            FundRaising._meta.get_field(name)
            return name
        except FieldDoesNotExist:
            continue
    return None


def dashboard_context(request, context):
    today_start, tomorrow_start = _today_bounds()
    month_start_dt, month_next_dt = _this_month_bounds()
    year_start_dt, year_next_dt = _this_year_bounds()
    today_date = timezone.localdate()

    users_agg = CustomUser.objects.aggregate(
        today=Count(Case(When(date_joined=today_date, then=1), output_field=IntegerField())),
        month=Count(Case(
            When(date_joined__gte=month_start_dt, date_joined__lt=month_next_dt, then=1),
            output_field=IntegerField(),
        )),
        year=Count(Case(
            When(date_joined__gte=year_start_dt, date_joined__lt=year_next_dt, then=1),
            output_field=IntegerField(),
        )),
        total=Count("id"),
    )

    funds_agg = FundRaising.objects.aggregate(
        today=Count(Case(
            When(start_date__gte=today_start, start_date__lt=tomorrow_start, then=1),
            output_field=IntegerField(),
        )),
        month=Count(Case(
            When(start_date__gte=month_start_dt, start_date__lt=month_next_dt, then=1),
            output_field=IntegerField(),
        )),
        year=Count(Case(
            When(start_date__gte=year_start_dt, start_date__lt=year_next_dt, then=1),
            output_field=IntegerField(),
        )),
        total=Count("id"),
        active=Count(Case(When(is_available=True, then=1), output_field=IntegerField())),
    )

    donors_agg = Donor.objects.aggregate(
        today=Count(Case(
            When(datetime__gte=today_start, datetime__lt=tomorrow_start, then=1),
            output_field=IntegerField(),
        )),
        month=Count(Case(
            When(datetime__gte=month_start_dt, datetime__lt=month_next_dt, then=1),
            output_field=IntegerField(),
        )),
        year=Count(Case(
            When(datetime__gte=year_start_dt, datetime__lt=year_next_dt, then=1),
            output_field=IntegerField(),
        )),
        total=Count("id"),
    )

    donation_sum = Donor.objects.aggregate(
        total_amount=Coalesce(Sum("amount"), Value(Decimal("0")), output_field=DecimalField()),
        month_amount=Coalesce(
            Sum(Case(
                When(datetime__gte=month_start_dt, datetime__lt=month_next_dt, then=F("amount")),
                default=Value(Decimal("0")),
                output_field=DecimalField(),
            )),
            Value(Decimal("0")),
            output_field=DecimalField(),
        ),
        today_amount=Coalesce(
            Sum(Case(
                When(datetime__gte=today_start, datetime__lt=tomorrow_start, then=F("amount")),
                default=Value(Decimal("0")),
                output_field=DecimalField(),
            )),
            Value(Decimal("0")),
            output_field=DecimalField(),
        ),
        year_amount=Coalesce(
            Sum(Case(
                When(datetime__gte=year_start_dt, datetime__lt=year_next_dt, then=F("amount")),
                default=Value(Decimal("0")),
                output_field=DecimalField(),
            )),
            Value(Decimal("0")),
            output_field=DecimalField(),
        ),
    )

    top_fund = (
        FundRaising.objects
        .order_by("-current_donation")
        .values("id", "title", "current_donation")
        .first()
    )

    # users chart series
    users_daily = _users_daily_series_last_n_days(90)
    users_monthly = _users_monthly_series_last_n_months(12)
    users_yearly = _users_yearly_series_last_n_years(5)

    # fundraising progress chart data (stacked bars)
    goal_field = _pick_goal_field()
    funds_qs = FundRaising.objects.order_by("-current_donation")[:10]

    f_labels, f_done, f_remain, f_pct = [], [], [], []
    for f in funds_qs:
        current = getattr(f, "current_donation", 0) or 0
        goal = (getattr(f, goal_field, 0) if goal_field else 0) or 0

        try:
            current = Decimal(str(current))
        except Exception:
            current = Decimal("0")

        try:
            goal = Decimal(str(goal))
        except Exception:
            goal = Decimal("0")

        # ✅ جلوگیری از تقسیم بر صفر / هدف منفی
        if goal <= 0:
            goal = current if current > 0 else Decimal("1")

        done = current if current <= goal else goal
        remain = goal - done if goal > done else Decimal("0")
        pct = int((done / goal) * 100) if goal > 0 else 0

        title = getattr(f, "title", None) or f"Fund #{f.pk}"
        f_labels.append(title[:18] + ("…" if len(title) > 18 else ""))
        f_done.append(float(done))
        f_remain.append(float(remain))
        f_pct.append(pct)

    context["kpis"] = {
        "users": users_agg,
        "funds": funds_agg,
        "donors": donors_agg,
        "donation_sum": {
            "today": donation_sum["today_amount"],
            "month": donation_sum["month_amount"],
            "year": donation_sum["year_amount"],
            "total": donation_sum["total_amount"],
        },
        "top_fund": top_fund,
    }

    context["charts"] = {
        "users_series": json.dumps(
            {"daily": users_daily, "monthly": users_monthly, "yearly": users_yearly},
            ensure_ascii=False,
        ),
        "funds_progress": json.dumps(
            {"labels": f_labels, "done": f_done, "remain": f_remain, "pct": f_pct},
            ensure_ascii=False,
        ),
    }

    return context
