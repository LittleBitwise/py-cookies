from http.cookiejar import CookieJar

from .cookies import load_cookies_from_firefox


def load(domain) -> CookieJar:
    return load_cookies_from_firefox(domain)


if __name__ == "__main__":
    argument = input("Enter domain: ")
    if argument:
        cookies = load(argument)
        print(cookies)
        print("Cookies:", len(cookies))
    else:
        print("No domain provided.")
