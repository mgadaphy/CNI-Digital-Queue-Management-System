import click
from flask.cli import FlaskGroup
from flask_migrate import Migrate, MigrateCommand
from app import create_app

# Use the app factory pattern
cli = FlaskGroup(create_app=create_app)

@cli.command("create_admin")
@click.argument("employee_id")
@click.argument("first_name")
@click.argument("last_name")
@click.argument("email")
@click.argument("password")
def create_admin(employee_id, first_name, last_name, email, password):
    """Creates a new administrative user."""
    from app import db
    from app.models import Agent

    if Agent.query.filter_by(email=email).first() or Agent.query.filter_by(employee_id=employee_id).first():
        print(f"Error: An agent with the same email or employee ID already exists.")
        return

    admin = Agent(
        employee_id=employee_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        role='admin'
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f"Admin user {first_name} {last_name} created successfully.")


if __name__ == '__main__':
    cli()
