import click
from flask import Flask

from .extensions import db
from .models import User, UserRole
from .services import InventoryService


def register_seed_commands(app: Flask) -> None:
    @app.cli.command("seed")
    def seed() -> None:
        """Create default locations and device types."""
        InventoryService.seed_defaults()
        app.logger.info("Seed data applied")

    @app.cli.command("create-superadmin")
    @click.argument("email")
    @click.argument("full_name")
    @click.password_option()
    def create_superadmin(email: str, full_name: str, password: str) -> None:
        """Create a super admin user."""
        if not email.endswith("@ittest-team.ru"):
            click.echo("Error: Email must be from @ittest-team.ru domain", err=True)
            return

        if User.query.filter_by(email=email).first():
            click.echo(f"Error: User with email {email} already exists", err=True)
            return

        user = User(
            email=email,
            full_name=full_name,
            role=UserRole.SUPER_ADMIN,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Super admin {email} created successfully")

    @app.cli.command("set-user-role")
    @click.argument("email")
    @click.argument("role", type=click.Choice(["super_admin", "admin", "user"]))
    def set_user_role(email: str, role: str) -> None:
        """Set role for existing user."""
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo(f"Error: User with email {email} not found", err=True)
            return

        user.role = UserRole[role.upper()]
        db.session.commit()
        click.echo(f"User {email} role updated to {role}")





