"""Management command: ensure the seller group exists and (optionally) add users to it."""

from __future__ import annotations

from argparse import ArgumentParser
from typing import Any, Optional, cast

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """
    Ensure the seller group exists and (optionally) add users to it.

    Usage examples:
        python manage.py ensure_seller_group
        python manage.py ensure_seller_group --user alice --user bob
        python manage.py ensure_seller_group --group merchants --user alice
    """

    help = "Ensure the seller group exists and optionally add users to it."

    def add_arguments(self, parser: ArgumentParser) -> None:
        """
        Define CLI arguments for the command.

        --user  Username to add to the group. May be passed multiple times.
        --group  Name of group  to use. Defaults to settings.SHOP_SELLER_GROUP or 'seller'.
        """
        parser.add_argument(
            "--user",
            action="append",
            type=str,
            default=[],
            metavar="USERNAME",
            help="Username to add to the seller group (can be given multiple times).",
        )
        parser.add_argument(
            "--group",
            type=str,
            default=None,
            metavar="GROUP",
            help="Group name (defaults to settings.SHOP_SELLER_GROUP or 'seller').",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        """
        Create the group if needed and add the provided users to it.

        Raises:
            CommandError: if any of the provided usernames do not exist.
        """
        group_opt = cast(Optional[str], opts.get("group"))
        group_name: str = group_opt or cast(str, getattr(settings, "SHOP_SELLER_GROUP", "seller"))
        group, _created = Group.objects.get_or_create(name=group_name)
        self.stdout.write(self.style.SUCCESS(f"Group '{group_name}' is present."))

        usernames_opt = opts.get("user")
        usernames: list[str] = cast(list[str], usernames_opt or [])

        if not usernames:
            return

        user_model = get_user_model()
        username_field: str = cast(str, getattr(user_model, "USERNAME_FIELD", "username"))

        missing: list[str] = []
        for username in usernames:
            user = user_model.objects.filter(**{username_field: username}).first()
            if not user:
                missing.append(username)
                continue

            # Avoid `user.groups` for better type-checker compatibility:
            group.user_set.add(user)  # idempotent; no explicit save() needed
            self.stdout.write(self.style.SUCCESS(f"Added '{username}' to '{group_name}'."))

        if missing:
            raise CommandError(f"User(s) not found: {', '.join(missing)}")
