import unittest

from py_cookies.cookies import _domain_matches


class DomainMatchesTests(unittest.TestCase):
    def test_exact_and_subdomain_hosts_match(self) -> None:
        self.assertTrue(_domain_matches("example.com", "example.com"))
        self.assertTrue(_domain_matches("sub.example.com", "example.com"))
        self.assertTrue(_domain_matches(".example.com", "example.com"))

    def test_partial_suffix_does_not_match(self) -> None:
        self.assertFalse(_domain_matches("longexample.com", "example.com"))

    def test_match_is_case_insensitive(self) -> None:
        self.assertTrue(_domain_matches("Sub.Example.COM", "example.com"))

    def test_empty_domain_matches_all(self) -> None:
        self.assertTrue(_domain_matches("example.com", ""))


if __name__ == "__main__":
    unittest.main()
