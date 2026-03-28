#!/usr/bin/env python3
"""
E2E Backend Endpoint Verification Script

Tests all backend API endpoints and reports:
- HTTP status codes
- Response times
- Success/failure summary

Usage:
    python e2e_verify_endpoints.py [--base-url http://localhost:8000]
"""

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Install with: pip install requests")
    sys.exit(1)


# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


@dataclass
class EndpointTest:
    """Represents a single endpoint test"""
    method: str
    path: str
    requires_auth: bool = True
    body: Optional[Dict] = None
    description: str = ""
    expected_status: int = 200


@dataclass
class TestResult:
    """Represents the result of an endpoint test"""
    endpoint: EndpointTest
    status_code: int
    response_time_ms: float
    success: bool
    error: Optional[str] = None


class EndpointVerifier:
    """E2E endpoint verification tool"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api/v1"
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.results: List[TestResult] = []

    def _make_request(
        self,
        method: str,
        path: str,
        requires_auth: bool = True,
        body: Optional[Dict] = None,
        timeout: int = 10
    ) -> Tuple[int, float, Optional[str]]:
        """
        Make HTTP request and return (status_code, response_time_ms, error)
        """
        url = f"{self.api_base}{path}"
        headers = {}

        if requires_auth and self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"

        try:
            start = time.time()

            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=body, headers=headers, timeout=timeout)
            elif method == 'PATCH':
                response = requests.patch(url, json=body, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            elapsed = (time.time() - start) * 1000  # Convert to ms
            return response.status_code, elapsed, None

        except requests.exceptions.Timeout:
            return 0, timeout * 1000, "Request timeout"
        except requests.exceptions.ConnectionError:
            return 0, 0, "Connection failed"
        except Exception as e:
            return 0, 0, str(e)

    def setup_auth(self) -> bool:
        """
        Attempt to authenticate with test credentials
        Returns True if successful, False otherwise
        """
        print(f"\n{Colors.CYAN}Setting up authentication...{Colors.RESET}")

        # Try to register a test user
        test_email = "e2e_test@example.com"
        test_password = "E2ETestPassword123!"

        register_body = {
            "email": test_email,
            "password": test_password,
            "password_confirm": test_password
        }

        status, _, _ = self._make_request(
            'POST',
            '/auth/register',
            requires_auth=False,
            body=register_body
        )

        # Registration might fail if user exists (409) - that's OK
        if status in [201, 409]:
            print(f"{Colors.GREEN}✓ Test user ready (status {status}){Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}! Registration returned {status} - continuing anyway{Colors.RESET}")

        # Try to login
        login_body = {
            "email": test_email,
            "password": test_password
        }

        try:
            url = f"{self.api_base}/auth/login"
            response = requests.post(url, json=login_body, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')

                if self.access_token:
                    print(f"{Colors.GREEN}✓ Authentication successful{Colors.RESET}")
                    return True
                else:
                    print(f"{Colors.RED}✗ No access token in response{Colors.RESET}")
                    return False
            else:
                print(f"{Colors.RED}✗ Login failed with status {response.status_code}{Colors.RESET}")
                return False

        except Exception as e:
            print(f"{Colors.RED}✗ Authentication error: {e}{Colors.RESET}")
            return False

    def run_test(self, endpoint: EndpointTest) -> TestResult:
        """Run a single endpoint test"""
        status, elapsed, error = self._make_request(
            endpoint.method,
            endpoint.path,
            endpoint.requires_auth,
            endpoint.body
        )

        success = (status == endpoint.expected_status and error is None)

        return TestResult(
            endpoint=endpoint,
            status_code=status,
            response_time_ms=elapsed,
            success=success,
            error=error
        )

    def print_result(self, result: TestResult):
        """Print colored test result"""
        status_color = Colors.GREEN if result.success else Colors.RED
        status_symbol = "✓" if result.success else "✗"

        method_colored = f"{Colors.BOLD}{result.endpoint.method}{Colors.RESET}"

        status_text = f"{result.status_code}" if result.status_code else "FAIL"
        time_text = f"{result.response_time_ms:.0f}ms" if result.response_time_ms else "N/A"

        print(
            f"{status_color}{status_symbol}{Colors.RESET} "
            f"{method_colored:6} {result.endpoint.path:50} "
            f"[{status_text:3}] {time_text:>7} "
            f"{Colors.CYAN}{result.endpoint.description}{Colors.RESET}"
        )

        if result.error:
            print(f"  {Colors.RED}Error: {result.error}{Colors.RESET}")

    def run_all_tests(self):
        """Run all endpoint tests"""

        # Define all endpoints to test
        endpoints = [
            # ===== Auth Endpoints =====
            EndpointTest('POST', '/auth/register', False,
                         {"email": "new@test.com", "password": "Pass123!", "password_confirm": "Pass123!"},
                         "Register new user", 201),
            EndpointTest('POST', '/auth/login', False,
                         {"email": "e2e_test@example.com", "password": "E2ETestPassword123!"},
                         "User login", 200),
            EndpointTest('POST', '/auth/verify-email', False,
                         {"email": "test@test.com", "code": "123456"},
                         "Verify email (expected 400)", 400),
            EndpointTest('POST', '/auth/resend-otp', False,
                         {"email": "test@test.com"},
                         "Resend OTP", 200),
            EndpointTest('POST', '/auth/refresh', False,
                         {"refresh_token": self.refresh_token or "invalid"},
                         "Refresh token", 200),
            EndpointTest('POST', '/auth/logout', True, None,
                         "Logout", 200),

            # 2FA Endpoints
            EndpointTest('POST', '/auth/2fa/reauth', True,
                         {"password": "E2ETestPassword123!"},
                         "2FA reauth", 200),
            EndpointTest('POST', '/auth/2fa/setup', True, None,
                         "2FA setup", 200),
            EndpointTest('POST', '/auth/2fa/verify', True,
                         {"code": "123456"},
                         "2FA verify (expected 400)", 400),
            EndpointTest('POST', '/auth/2fa/validate', True,
                         {"code": "123456"},
                         "2FA validate (expected 400)", 400),
            EndpointTest('POST', '/auth/2fa/disable', True,
                         {"password": "E2ETestPassword123!", "code": "123456"},
                         "2FA disable (expected 400)", 400),
            EndpointTest('GET', '/auth/2fa/status', True, None,
                         "2FA status", 200),

            # ===== VPN Endpoints =====
            EndpointTest('GET', '/vpn/usage', True, None,
                         "VPN usage stats", 200),

            # ===== Wallet Endpoints =====
            EndpointTest('GET', '/wallet/balance', True, None,
                         "Wallet balance", 200),
            EndpointTest('GET', '/wallet/transactions', True, None,
                         "Wallet transactions", 200),
            EndpointTest('POST', '/wallet/withdraw', True,
                         {"amount": 10.0, "method": "cryptobot"},
                         "Wallet withdraw", 200),

            # ===== Payment Endpoints =====
            EndpointTest('POST', '/payments/invoice', True,
                         {"user_uuid": "test-uuid", "plan_id": "plan_monthly", "currency": "USD"},
                         "Create invoice", 201),
            EndpointTest('GET', '/payments/invoice/inv_test', True, None,
                         "Get invoice status (expected 404)", 404),
            EndpointTest('GET', '/payments/history', True, None,
                         "Payment history", 200),

            # ===== Subscription Endpoints =====
            EndpointTest('GET', '/subscriptions/', True, None,
                         "List subscriptions", 200),
            EndpointTest('GET', '/subscriptions/test-uuid', True, None,
                         "Get subscription (expected 404)", 404),
            EndpointTest('GET', '/subscriptions/config/user-uuid', True, None,
                         "Get VPN config (expected 404)", 404),

            # ===== Codes Endpoints =====
            EndpointTest('POST', '/codes/validate', True,
                         {"code": "TESTCODE"},
                         "Validate promo code (expected 404)", 404),

            # ===== Referral Endpoints =====
            EndpointTest('GET', '/referral/status', True, None,
                         "Referral status", 200),
            EndpointTest('GET', '/referral/code', True, None,
                         "Referral code (expected 404)", 404),
            EndpointTest('GET', '/referral/stats', True, None,
                         "Referral stats", 200),
            EndpointTest('GET', '/referral/recent', True, None,
                         "Recent commissions", 200),

            # ===== Profile Endpoints =====
            EndpointTest('GET', '/users/me/profile', True, None,
                         "Get profile", 200),
            EndpointTest('PATCH', '/users/me/profile', True,
                         {"display_name": "Test User"},
                         "Update profile", 200),

            # ===== Security Endpoints =====
            EndpointTest('POST', '/security/change-password', True,
                         {"current_password": "wrong", "new_password": "NewPass123!"},
                         "Change password (expected 401)", 401),
            EndpointTest('GET', '/security/antiphishing', True, None,
                         "Get antiphishing code", 200),
            EndpointTest('POST', '/security/antiphishing', True,
                         {"code": "TestCode123"},
                         "Set antiphishing code", 200),
            EndpointTest('DELETE', '/security/antiphishing', True, None,
                         "Delete antiphishing code (expected 404)", 404),

            # ===== Trial Endpoints =====
            EndpointTest('POST', '/trial/activate', True, None,
                         "Activate trial", 200),
            EndpointTest('GET', '/trial/status', True, None,
                         "Trial status", 200),
        ]

        print(f"\n{Colors.BOLD}{'='*100}{Colors.RESET}")
        print(f"{Colors.BOLD}E2E Endpoint Verification{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*100}{Colors.RESET}\n")

        # Run all tests
        for endpoint in endpoints:
            result = self.run_test(endpoint)
            self.results.append(result)
            self.print_result(result)

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success)
        failed = total - passed

        avg_time = sum(r.response_time_ms for r in self.results if r.response_time_ms) / total

        print(f"\n{Colors.BOLD}{'='*100}{Colors.RESET}")
        print(f"{Colors.BOLD}Summary{Colors.RESET}\n")
        print(f"  Total endpoints tested: {total}")
        print(f"  {Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"  {Colors.RED}Failed: {failed}{Colors.RESET}")
        print(f"  Average response time: {avg_time:.0f}ms")
        print(f"{Colors.BOLD}{'='*100}{Colors.RESET}\n")

        if failed == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}✓ All endpoint tests passed!{Colors.RESET}\n")
            return 0
        else:
            print(f"{Colors.RED}{Colors.BOLD}✗ {failed} endpoint test(s) failed{Colors.RESET}\n")
            return 1


def main():
    parser = argparse.ArgumentParser(description='E2E Backend Endpoint Verification')
    parser.add_argument(
        '--base-url',
        default='http://localhost:8000',
        help='Backend API base URL (default: http://localhost:8000)'
    )
    args = parser.parse_args()

    verifier = EndpointVerifier(args.base_url)

    # Setup authentication
    if not verifier.setup_auth():
        print(f"\n{Colors.YELLOW}Warning: Authentication failed, some tests may fail{Colors.RESET}")
        print(f"{Colors.YELLOW}Continuing with unauthenticated tests...{Colors.RESET}\n")

    # Run all tests
    verifier.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if all(r.success for r in verifier.results) else 1)


if __name__ == '__main__':
    main()
