"""
ASGI config for shopping_bot project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application
from django_mcp.asgi import mount_mcp_server

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mcp_project.settings')

django_asgi_app = get_asgi_application()

application = mount_mcp_server(
    django_asgi_app,
    mcp_base_path="/mcp/"
)
