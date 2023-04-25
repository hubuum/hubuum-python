"""Non-versioned views for hubuum."""

from knox.views import LoginView as KnoxLoginView
from knox.views import LogoutAllView as KnoxLogoutAllView
from knox.views import LogoutView as KnoxLogoutView
from rest_framework.authentication import BasicAuthentication
from rest_framework.schemas.openapi import AutoSchema

# Note, we set schemas simply to ensure that openapi is generated correctly.


# Allow basic auth to the Knox login view.
#
# We use Knox everywhere, but we need to be able to get Knox tokens somehow.
# To achieve this, we disable Knox for the LoginView.
# https://james1345.github.io/django-rest-knox/auth/#global-usage-on-all-views
class LoginView(KnoxLoginView):
    """Login view that allows basic auth."""

    schema = AutoSchema(
        tags=["Authentication"],
    )

    authentication_classes = [BasicAuthentication]


class LogoutView(KnoxLogoutView):
    """Logout view that sets schema correctly.."""

    schema = AutoSchema(
        tags=["Authentication"],
    )


class LogoutAllView(KnoxLogoutAllView):
    """Logout all view that sets schema correctly.."""

    schema = AutoSchema(
        tags=["Authentication"],
    )
