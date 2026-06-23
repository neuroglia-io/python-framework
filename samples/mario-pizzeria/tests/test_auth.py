#!/usr/bin/env python3
"""
Test script for Mario's Pizzeria authentication and profile management.

This script tests:
1. Keycloak authentication
2. Automatic profile creation
3. Profile retrieval
"""

import asyncio

import httpx
from rich.console import Console
from rich.table import Table

console = Console()

BASE_URL = "http://localhost:8080"

# Test users from Keycloak
TEST_USERS = [
    {"username": "customer", "password": "password123", "expected_name": "Mario Customer"},
    {"username": "chef", "password": "password123", "expected_name": "Luigi Chef"},
    {"username": "manager", "password": "password123", "expected_name": "Mario Manager"},
]


async def test_login(client: httpx.AsyncClient, username: str, password: str):
    """Test login and return session cookies"""
    console.print(f"[cyan]Testing login for: {username}[/cyan]")

    response = await client.post(
        f"{BASE_URL}/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )

    if response.status_code == 303:
        console.print(f"  [green]✓[/green] Login successful (redirect to {response.headers.get('location')})")
        return True
    else:
        console.print(f"  [red]✗[/red] Login failed: {response.status_code}")
        return False


async def test_profile_api(client: httpx.AsyncClient, username: str):
    """Test profile API endpoint"""
    console.print(f"[cyan]Testing profile API for: {username}[/cyan]")

    # Get profile via API (requires user_id header in production)
    response = await client.get(f"{BASE_URL}/api/profile/me")

    if response.status_code == 200:
        profile = response.json()
        console.print(f"  [green]✓[/green] Profile retrieved")
        console.print(f"    Name: {profile.get('name')}")
        console.print(f"    Email: {profile.get('email')}")
        console.print(f"    Total Orders: {profile.get('total_orders', 0)}")
        return True
    else:
        console.print(f"  [yellow]⚠[/yellow] Profile API returned: {response.status_code}")
        return False


async def test_user_flow(username: str, password: str, expected_name: str):
    """Test complete user flow"""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Test login
        login_success = await test_login(client, username, password)
        if not login_success:
            return False

        # Test profile API
        await test_profile_api(client, username)

        # Test logout
        console.print(f"[cyan]Testing logout for: {username}[/cyan]")
        response = await client.get(f"{BASE_URL}/auth/logout", follow_redirects=False)
        if response.status_code == 303:
            console.print(f"  [green]✓[/green] Logout successful\n")
            return True
        else:
            console.print(f"  [red]✗[/red] Logout failed: {response.status_code}\n")
            return False


async def main():
    """Main test execution"""
    console.print("\n[bold cyan]🍕 Mario's Pizzeria Authentication Test Suite[/bold cyan]\n")

    results = []

    for user in TEST_USERS:
        console.rule(f"[bold yellow]Testing {user['username']}[/bold yellow]")
        success = await test_user_flow(user["username"], user["password"], user["expected_name"])
        results.append({"user": user["username"], "success": success})
        await asyncio.sleep(1)

    # Print summary
    console.rule("[bold green]Test Summary[/bold green]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("User", style="cyan")
    table.add_column("Status", justify="center")

    for result in results:
        status = "[green]✓ PASSED[/green]" if result["success"] else "[red]✗ FAILED[/red]"
        table.add_row(result["user"], status)

    console.print(table)

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    console.print(f"\n[bold]Results: {passed}/{total} tests passed[/bold]\n")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
