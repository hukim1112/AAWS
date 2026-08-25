"""Prime Number Calculator.

Finds all prime numbers between 1 and 100 and displays the results.
"""

from typing import List


def is_prime(n: int) -> bool:
    """Check whether a given integer n is a prime number.

    Args:
        n: The integer to check.

    Returns:
        True if n is prime, False otherwise.
    """
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False

    # Check divisors up to sqrt(n)
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def find_primes_in_range(start: int, end: int) -> List[int]:
    """Find all prime numbers in the inclusive range [start, end].

    Args:
        start: Lower bound of the range.
        end: Upper bound of the range.

    Returns:
        A list of prime numbers in ascending order.
    """
    return [num for num in range(start, end + 1) if is_prime(num)]


def main() -> None:
    """Main execution function."""
    start, end = 1, 100
    primes = find_primes_in_range(start, end)

    print(f"=== {start}부터 {end}까지의 소수 탐색 결과 ===")
    print(f"소수 총 개수: {len(primes)}개")
    print(f"소수 목록:\n{primes}")


if __name__ == "__main__":
    main()
