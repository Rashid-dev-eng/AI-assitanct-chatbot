from unittest.mock import Mock

from django.test import SimpleTestCase
import requests

from integrations.moodle.adapter import MoodleAdapter, MoodleConfig
from integrations.moodle.exceptions import MoodleAuthenticationError, MoodleNotConfigured, MoodleUnavailable


def config(**changes):
    values = dict(enabled=True, rest_url="https://moodle.example/webservice/rest/server.php",
                  service_token="secret-token", allowed_functions={"site_info": "core_webservice_get_site_info"},
                  max_retries=1)
    values.update(changes)
    return MoodleConfig(**values)


class MoodleAdapterTests(SimpleTestCase):
    def test_disabled_adapter_never_calls_network(self):
        session = Mock()
        adapter = MoodleAdapter(config(enabled=False), session=session)
        self.assertEqual(adapter.status()["status"], "disabled")
        with self.assertRaises(MoodleNotConfigured):
            adapter.call_read_only("site_info")
        session.post.assert_not_called()

    def test_status_does_not_expose_secret_or_endpoint(self):
        adapter = MoodleAdapter(config())
        status = str(adapter.status())
        self.assertNotIn("secret-token", status)
        self.assertNotIn("moodle.example", status)
        self.assertEqual(adapter.status()["status"], "configured_unverified")

    def test_allowlisted_call_posts_token_over_verified_https(self):
        session = Mock()
        response = Mock(status_code=200)
        response.json.return_value = {"sitename": "Test"}
        session.post.return_value = response
        adapter = MoodleAdapter(config(), session=session)
        self.assertEqual(adapter.call_read_only("site_info"), {"sitename": "Test"})
        kwargs = session.post.call_args.kwargs
        self.assertEqual(kwargs["data"]["wstoken"], "secret-token")
        self.assertEqual(kwargs["data"]["wsfunction"], "core_webservice_get_site_info")
        self.assertTrue(kwargs["verify"])
        self.assertFalse(kwargs["allow_redirects"])

    def test_write_function_cannot_be_added_by_configuration(self):
        adapter = MoodleAdapter(config(allowed_functions={"delete": "core_user_delete_users"}))
        with self.assertRaises(MoodleNotConfigured):
            adapter.call_read_only("delete")

    def test_timeout_retries_are_bounded_and_sanitized(self):
        session = Mock()
        session.post.side_effect = requests.Timeout("secret-token must not leak")
        adapter = MoodleAdapter(config(max_retries=1), session=session)
        with self.assertRaises(MoodleUnavailable) as raised:
            adapter.call_read_only("site_info")
        self.assertEqual(session.post.call_count, 2)
        self.assertNotIn("secret-token", str(raised.exception))

    def test_auth_rejection_is_reported_safely(self):
        session = Mock()
        session.post.return_value = Mock(status_code=403)
        adapter = MoodleAdapter(config(), session=session)
        with self.assertRaises(MoodleAuthenticationError):
            adapter.call_read_only("site_info")

    def test_moodle_error_payload_does_not_leak_body(self):
        session = Mock()
        response = Mock(status_code=200)
        response.json.return_value = {"exception": "moodle_exception", "message": "private details", "errorcode": "invalidtoken"}
        session.post.return_value = response
        adapter = MoodleAdapter(config(), session=session)
        with self.assertRaises(MoodleAuthenticationError) as raised:
            adapter.call_read_only("site_info")
        self.assertNotIn("private details", str(raised.exception))
