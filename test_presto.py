import pytest
import transaction
from trees.tests.utils import start_order, fill_in_delivery_details, \
    confirm_delivery, logout

from trees.usermodels import User

# Request test accounts from prestodoctor.com
PRESTO_USER_WITH_RECOMMENDATION = ""
PRESTO_USER_WITHOUT_RECOMMENDATION = ""
PRESTO_PASSWORD = ""
PHONE_NUMBER = ""


@pytest.fixture
def non_evaluated_user_browser(request, browser_instance_getter):
    """Selenium/slinter/pytest-splinter does not properly clean the browser between tests.

    https://github.com/pytest-dev/pytest-splinter/issues/49
    """
    return browser_instance_getter(request, non_evaluated_user_browser)


def do_presto_login(browser, presto_user=PRESTO_USER_WITH_RECOMMENDATION, presto_password=PRESTO_PASSWORD):
    """This will cause an alert in your Presto login management which you need to clear later."""
    b = browser

    assert b.is_text_present("Sign in to your account")

    # Fill in Presto login page
    b.fill("user[email]", presto_user)
    b.fill("user[password]", presto_password)
    b.find_by_css("input[name='commit']").click()

    # First time login pops up allow permission dialog.
    if b.is_text_present("Authorization required"):
        b.find_by_css("input[name='commit']").click()


def do_presto_login_if_needed(browser, presto_user=PRESTO_USER_WITH_RECOMMENDATION, presto_password=PRESTO_PASSWORD):
    """For subsequent tests the Prestodoctor auth keys remain activate and we don't need to enter username and password again.

     Redirecting through OAuth provider endpoint is enough."""

    if browser.is_text_present("Sign in to your account"):
        do_presto_login(browser, presto_user, presto_password)


def test_presto_login(web_server, browser, DBSession, init):
    """Login / sign up with Prestodoctor.

    Presto application must be configurd as web application, running in http://localhost:8521/.

    Example invocation: PRESTO_USER="040xxxXXXX" PRESTO_PASSWORD="yyyy"  py.test trees -s --splinter-webdriver=firefox --splinter-make-screenshot-on-failure=false --ini=test.ini -k test_facebook_login

    :param web_server: Py.text fixture, gives HTTP address where the functional test web server is running, ``http://localhost:8521/``
    :param browser: Py.test Splinter Browser fixture
    :param DBSession: Py.test SQLALchemy session
    :param init: Websauna configuration object
    """
    b = browser

    # Initiate Presto login with Authomatic
    b.visit("{}/login".format(web_server))
    b.find_by_css(".btn-login-prestodoctor").click()

    do_presto_login_if_needed(b)

    assert b.is_text_present("You are now logged in")

    # See that we got somewhat sane data
    with transaction.manager:
        assert DBSession.query(User).count() == 1
        u = DBSession.query(User).get(1)
        assert u.first_login
        assert u.email == PRESTO_USER_WITH_RECOMMENDATION
        assert u.activated_at
        assert u.last_login_ip == "127.0.0.1"

        # Check user basic data
        assert u.full_name == 'Test Oauth1'
        assert u.user_data["social"]["prestodoctor"]["dob"] == -621648001
        assert u.address == "123 MARKET ST"
        assert u.city == "SAN FRANCISCO"
        assert u.state == "CA"
        assert u.zipcode == "94105"

        # License details
        assert u.presto_license_number == 692624515
        assert u.medical_license_upload_completed_at
        assert u.driving_license_upload_completed_at
        assert u.license_initial_upload_completed_at

    # Generated by our backend on succesful oauth login
    assert b.is_text_present("You are now logged in")

    logout(web_server, b)
    assert b.is_text_present("You are now logged out")


def test_presto_double_login(web_server, browser, DBSession, init):
    """Login Presto user twice and see we do heavy data import only once."""

    b = browser

    # Initiate Presto login with Authomatic
    b.visit("{}/login".format(web_server))
    b.find_by_css(".btn-login-prestodoctor").click()

    do_presto_login_if_needed(b)

    assert b.is_text_present("You are now logged in")

    # See that we got somewhat sane data
    with transaction.manager:
        assert DBSession.query(User).count() == 1
        u = DBSession.query(User).get(1)

        # Grab timestamp of full data update
        full_data_updated_at = u.user_data["social"]["prestodoctor"]["full_data_updated_at"]

    logout(web_server, b)

    # Go again
    b.visit("{}/login".format(web_server))
    b.find_by_css(".btn-login-prestodoctor").click()
    do_presto_login_if_needed(b)

    assert b.is_text_present("You are now logged in")

    with transaction.manager:
        assert DBSession.query(User).count() == 1
        u = DBSession.query(User).get(1)

        # Grab timestamp of full data update
        assert u.user_data["social"]["prestodoctor"]["full_data_updated_at"] == full_data_updated_at


def test_presto_non_evaluated_user(web_server, non_evaluated_user_browser, DBSession, init):
    """Login Presto user who has not evaluation done yet."""

    b = non_evaluated_user_browser

    # Initiate Presto login with Authomatic
    b.visit("{}/login".format(web_server))
    b.find_by_css(".btn-login-prestodoctor").click()

    do_presto_login_if_needed(b, presto_user=PRESTO_USER_WITHOUT_RECOMMENDATION)

    assert b.is_text_present("You are now logged in")

    # See that we got somewhat sane data
    with transaction.manager:
        assert DBSession.query(User).count() == 1
        u = DBSession.query(User).get(1)
        assert u.first_login
        assert u.email == PRESTO_USER_WITHOUT_RECOMMENDATION
        assert u.activated_at
        assert u.last_login_ip == "127.0.0.1"

        # Check user basic data
        assert u.full_name == 'Test Oauth2'
        assert u.user_data["social"]["prestodoctor"]["dob"] == -621648001
        assert u.address == "123 MARKET ST"
        assert u.city == "SAN FRANCISCO"
        assert u.state == "CA"
        assert u.zipcode == "94105"

        # License details should be empty
        assert not u.presto_license_number
        assert not u.medical_license_upload_completed_at
        assert not u.driving_license_upload_completed_at
        assert not u.license_initial_upload_completed_at


def test_presto_order(web_server, browser, DBSession, init):
    """Do direct-to-buy now with licenced presto user.

    This should go directly to thank you page, no medical evaluation questions needed.
    """
    b = browser

    start_order(web_server, browser, init, login_needed=False)

    assert b.is_text_present("Sign in to buy")
    b.find_by_css(".btn-login-prestodoctor").click()
    do_presto_login_if_needed(b)

    # Generated by our backend on succesful oauth login
    assert b.is_text_present("You are now logged in")
    assert b.is_text_present("Checkout")

    # Assert we are on the order page
    fill_in_delivery_details(b, phone_number=PHONE_NUMBER, email=None)
    confirm_delivery(b, membership=True)

    assert b.is_element_visible_by_css("#thank-you")


def test_presto_order_non_evaluated_user(web_server, non_evaluated_user_browser, DBSession, init):
    """Do direct-to-buy now with licenced presto user.

    This should go directly to thank you page, no medical evaluation questions needed.
    """
    b = non_evaluated_user_browser

    start_order(web_server, b, init, login_needed=False)

    assert b.is_text_present("Sign in to buy")
    b.find_by_css(".btn-login-prestodoctor").click()
    do_presto_login_if_needed(b, presto_user=PRESTO_USER_WITHOUT_RECOMMENDATION)

    # Generated by our backend on succesful oauth login
    assert b.is_text_present("You are now logged in")
    assert b.is_text_present("Checkout")

    # Assert we are on the order page
    fill_in_delivery_details(b, phone_number=PHONE_NUMBER, email=None)
    confirm_delivery(b, membership=True)

    assert b.is_element_visible_by_css("#medical-recommendation")
