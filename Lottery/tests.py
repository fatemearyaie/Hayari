from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from Lottery.models import Lottery, LotteryRewards
from Lottery.serializers.lottery_serializers import (
    ActiveLotterySerializer,
    LastLotteryUserStatusSerializer,
    LotteryRewardSerializer,
)
from Lottery.tasks import run_active_lottery
from Notification.models.notification_models import UserFCMToken, UserNotification
from Users.models import CustomUser


def create_user(email, month_score=0, balance=Decimal("0")):
    return CustomUser.objects.create_user(
        email=email,
        month_score=month_score,
        balance=balance,
    )


def auth_headers(user):
    token = AccessToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "lottery-tests",
        }
    }
)
class LotteryModelAndTaskTests(TestCase):
    def setUp(self):
        self.user = create_user("lottery-user@example.com", month_score=10)
        self.other_user = create_user("lottery-other@example.com", month_score=5)

    def create_lottery(self, **kwargs):
        values = {
            "name": "Monthly lottery",
            "lottery_datetime": timezone.now() - timedelta(minutes=1),
            "description": "Monthly rewards",
            "is_active": True,
        }
        values.update(kwargs)
        return Lottery.objects.create(**values)

    def test_saving_active_lottery_deactivates_previous_active_record(self):
        first = self.create_lottery(name="First")
        second = self.create_lottery(name="Second")
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)
        self.assertEqual(Lottery.objects.filter(is_active=True).count(), 1)

    def test_lottery_serializers_include_nested_rewards_and_user(self):
        lottery = self.create_lottery()
        reward = LotteryRewards.objects.create(
            lottery=lottery,
            place=1,
            amount=500,
            user=self.user,
        )
        active = ActiveLotterySerializer(lottery).data
        reward_data = LotteryRewardSerializer(reward).data
        status_data = LastLotteryUserStatusSerializer({
            "lottery": lottery,
            "status": "win",
            "reward": reward,
        }).data
        self.assertEqual(active["name"], "Monthly lottery")
        self.assertEqual(active["rewards"][0]["place"], 1)
        self.assertEqual(reward_data["user"]["id"], self.user.id)
        self.assertEqual(status_data["status"], "win")
        self.assertEqual(status_data["reward"]["amount"], "500")

    def test_task_returns_no_active_lottery(self):
        self.assertEqual(run_active_lottery.run(), {"status": "no_active_lottery"})

    def test_task_returns_when_lottery_time_is_not_reached(self):
        lottery = self.create_lottery(lottery_datetime=timezone.now() + timedelta(minutes=5))
        result = run_active_lottery.run()
        self.assertEqual(result, {"status": "lottery_time_not_reached"})
        lottery.refresh_from_db()
        self.assertTrue(lottery.is_active)

    def test_task_deactivates_lottery_without_rewards(self):
        lottery = self.create_lottery()
        result = run_active_lottery.run()
        self.assertEqual(result, {"status": "no_rewards"})
        lottery.refresh_from_db()
        self.assertFalse(lottery.is_active)
        self.assertFalse(LotteryRewards.objects.exists())
        self.assertFalse(UserNotification.objects.exists())

    def test_task_deactivates_lottery_without_eligible_users(self):
        self.user.month_score = 0
        self.user.save(update_fields=["month_score"])
        self.other_user.month_score = 0
        self.other_user.save(update_fields=["month_score"])
        lottery = self.create_lottery()
        reward = LotteryRewards.objects.create(lottery=lottery, place=1, amount=100)
        result = run_active_lottery.run()
        self.assertEqual(result, {"status": "no_eligible_users"})
        lottery.refresh_from_db()
        self.assertFalse(lottery.is_active)
        reward.refresh_from_db()
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()
        self.assertIsNone(reward.user_id)
        self.assertEqual(self.user.balance, Decimal("0"))
        self.assertEqual(self.other_user.balance, Decimal("0"))
        self.assertFalse(UserNotification.objects.exists())

    @patch("Lottery.tasks.send_firebase_task.delay")
    @patch("Lottery.tasks.random.choices")
    def test_task_assigns_unique_winners_and_defers_firebase_dispatch(
        self,
        choices,
        lottery_delay,
    ):
        lottery = self.create_lottery()
        first_reward = LotteryRewards.objects.create(lottery=lottery, place=1, amount=100)
        second_reward = LotteryRewards.objects.create(lottery=lottery, place=2, amount=50)
        UserFCMToken.objects.create(user=self.user, token="winner-token")
        choice_calls = []
        winner_choices = iter([[self.user.id], [self.other_user.id]])

        def choose_winner(pool_ids, weights, k):
            choice_calls.append((list(pool_ids), list(weights), k))
            return next(winner_choices)

        choices.side_effect = choose_winner

        with self.captureOnCommitCallbacks(execute=True):
            result = run_active_lottery.run()

        self.assertEqual(result["status"], "done")
        self.assertEqual(result["winners"], [self.user.id, self.other_user.id])
        self.assertEqual(set(result["winners"]), {self.user.id, self.other_user.id})
        self.assertEqual(choices.call_count, 2)
        self.assertEqual(len(choice_calls), 2)
        first_pool, first_weights, first_count = choice_calls[0]
        second_pool, second_weights, second_count = choice_calls[1]
        self.assertEqual(set(first_pool), {self.user.id, self.other_user.id})
        self.assertEqual(dict(zip(first_pool, first_weights)), {self.user.id: 10, self.other_user.id: 5})
        self.assertEqual(first_count, 1)
        self.assertEqual(second_pool, [self.other_user.id])
        self.assertEqual(second_weights, [5])
        self.assertEqual(second_count, 1)
        first_reward.refresh_from_db()
        second_reward.refresh_from_db()
        self.assertEqual(first_reward.user_id, self.user.id)
        self.assertEqual(second_reward.user_id, self.other_user.id)
        self.user.refresh_from_db()
        self.other_user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("100"))
        self.assertEqual(self.other_user.balance, Decimal("50"))
        self.assertEqual(UserNotification.objects.filter(user=self.user).count(), 1)
        self.assertEqual(UserNotification.objects.filter(user=self.other_user).count(), 1)
        lottery.refresh_from_db()
        self.assertFalse(lottery.is_active)
        winner_notification = UserNotification.objects.get(user=self.user)
        lottery_delay.assert_any_call({
            "fcm": "winner-token",
            "title": "برنده قرعه‌کشی",
            "message": "تبریک! شما رتبه 1 را برنده شدید و مبلغ 100 به کیف پول شما اضافه شد.",
            "type": "lottery_win",
            "lottery_id": lottery.id,
            "place": 1,
            "amount": "100",
        })
        self.assertEqual(lottery_delay.call_count, 2)
        lottery_delay.assert_any_call({
            "title": winner_notification.title,
            "message": winner_notification.description,
            "fcm": "winner-token",
            "extra": {
                "type": "notification",
                "notification_id": str(winner_notification.id),
            },
        })


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "lottery-http-tests",
        }
    }
)
class LotteryHttpTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = create_user("lottery-http@example.com")
        self.other_user = create_user("lottery-http-other@example.com")

    def create_lottery(self, **kwargs):
        values = {
            "name": "HTTP lottery",
            "lottery_datetime": timezone.now(),
            "description": "HTTP description",
            "is_active": True,
        }
        values.update(kwargs)
        return Lottery.objects.create(**values)

    def test_lottery_endpoints_require_authentication(self):
        self.assertEqual(self.client.get("/api/v1/lottery/active/").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/lottery/status/").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/lottery/previous/winners/").status_code, 401)

    def test_active_endpoint_returns_nested_rewards_or_not_found(self):
        lottery = self.create_lottery()
        reward = LotteryRewards.objects.create(lottery=lottery, place=1, amount=100, user=self.user)
        response = self.client.get("/api/v1/lottery/active/", **auth_headers(self.user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["name"], "HTTP lottery")
        self.assertEqual(response.json()["data"]["rewards"][0]["place"], reward.place)

        lottery.is_active = False
        lottery.save(update_fields=["is_active"])
        missing = self.client.get("/api/v1/lottery/active/", **auth_headers(self.user))
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["data"]["detail"], "قرعه‌کشی فعالی وجود ندارد.")

    def test_previous_winners_filter_unassigned_rewards_and_order_results(self):
        previous = self.create_lottery(
            name="Previous",
            lottery_datetime=timezone.now() - timedelta(days=1),
            is_active=False,
        )
        LotteryRewards.objects.create(lottery=previous, place=2, amount=100, user=self.user)
        LotteryRewards.objects.create(lottery=previous, place=1, amount=200, user=self.other_user)
        LotteryRewards.objects.create(lottery=previous, place=3, amount=300, user=None)
        response = self.client.get(
            "/api/v1/lottery/previous/winners/",
            **auth_headers(self.user),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]["results"]
        self.assertEqual([item["place"] for item in data], [1, 2])
        self.assertEqual([item["amount"] for item in data], ["200", "100"])

    def test_last_lottery_status_reports_win_or_not_win(self):
        lottery = self.create_lottery(
            name="Last",
            lottery_datetime=timezone.now() - timedelta(days=1),
            is_active=False,
        )
        LotteryRewards.objects.create(lottery=lottery, place=1, amount=200, user=self.user)
        winner = self.client.get("/api/v1/lottery/status/", **auth_headers(self.user))
        not_winner = self.client.get("/api/v1/lottery/status/", **auth_headers(self.other_user))
        self.assertEqual(winner.status_code, 200)
        self.assertEqual(not_winner.status_code, 200)
        self.assertEqual(winner.json()["data"]["status"], "win")
        self.assertEqual(winner.json()["data"]["reward"]["amount"], "200")
        self.assertEqual(not_winner.json()["data"]["status"], "not_win")
        self.assertIsNone(not_winner.json()["data"]["reward"])

    def test_last_lottery_status_returns_not_found_without_lottery(self):
        response = self.client.get("/api/v1/lottery/status/", **auth_headers(self.user))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["data"]["اخطار"], "لاتاری پیدا نشد")
