from datetime import timedelta
from django.db.models import Count, Case, When, IntegerField, Sum, F, DecimalField, Value
from django.utils import timezone

from Users.models.users_models import CustomUser
from Funds.models.funds_models import FundRaising, Donor


def _today_bounds():
    now = timezone.localtime(timezone.now())
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _this_week_bounds():
    now = timezone.localtime(timezone.now())
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return monday, monday + timedelta(days=7)


def dashboard_context(request, context):
    # ---- time windows
    today_start, tomorrow_start = _today_bounds()
    week_start_dt, week_next_dt = _this_week_bounds()

    today_date = timezone.localdate()
    week_start_date = week_start_dt.date()
    week_end_exclusive = week_next_dt.date()

    # --- Users KPI
    users_agg = CustomUser.objects.aggregate(
        today=Count(Case(When(date_joined=today_date, then=1), output_field=IntegerField())),
        week=Count(Case(When(date_joined__gte=week_start_date, date_joined__lt=week_end_exclusive, then=1),
                        output_field=IntegerField())),
        total=Count("id"),
    )

    # --- Funds KPI
    funds_agg = FundRaising.objects.aggregate(
        today=Count(Case(When(start_date__gte=today_start, start_date__lt=tomorrow_start, then=1),
                         output_field=IntegerField())),
        week=Count(Case(When(start_date__gte=week_start_dt, start_date__lt=week_next_dt, then=1),
                        output_field=IntegerField())),
        total=Count("id"),
        active=Count(Case(When(is_available=True, then=1), output_field=IntegerField())),
    )

    # --- Donor KPIs (datetime = DateTimeField)
    donors_agg = Donor.objects.aggregate(
        today=Count(Case(When(datetime__gte=today_start, datetime__lt=tomorrow_start, then=1),
                         output_field=IntegerField())),
        week=Count(Case(When(datetime__gte=week_start_dt, datetime__lt=week_next_dt, then=1),
                        output_field=IntegerField())),
        total=Count("id"),
    )

    # --- Donation sums
    donation_sum = Donor.objects.aggregate(
        total_amount=Sum("amount"),
        week_amount=Sum(
            Case(
                When(datetime__gte=week_start_dt, datetime__lt=week_next_dt, then=F("amount")),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
        today_amount=Sum(
            Case(
                When(datetime__gte=today_start, datetime__lt=tomorrow_start, then=F("amount")),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
    )

    # --- Top fundraising by current_donation
    top_fund = (
        FundRaising.objects
        .order_by("-current_donation")
        .values("id", "title", "current_donation")
        .first()
    )

    context["kpis"] = {
        "users": users_agg,
        "funds": funds_agg,
        "donors": donors_agg,
        "donation_sum": {
            "today": donation_sum["today_amount"] or 0,
            "week": donation_sum["week_amount"] or 0,
            "total": donation_sum["total_amount"] or 0,
        },
        "top_fund": top_fund,
    }
    return context
