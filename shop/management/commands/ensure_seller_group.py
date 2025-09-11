from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Ensure the seller group exists and optionally add users to it."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            action="append",
            help="Username to add to the seller group (can be given multiple times).",
        )
        parser.add_argument(
            "--group",
            default=None,
            help="Group name (defaults to settings.SHOP_SELLER_GROUP or 'seller').",
        )

    def handle(self, *args, **opts):
        group_name = opts["group"] or getattr(settings, "SHOP_SELLER_GROUP", "seller")
        group, _ = Group.objects.get_or_create(name=group_name)
        self.stdout.write(self.style.SUCCESS(f"Group '{group_name}' is present."))

        usernames = opts.get("user") or []
        for username in usernames:
            user = User.objects.filter(username=username).first()
            if not user:
                raise CommandError(f"User '{username}' not found.")
            user.groups.add(group)
            user.save(update_fields=[])  # no-op save; group m2m already saved
            self.stdout.write(self.style.SUCCESS(f"Added '{username}' to '{group_name}'."))
