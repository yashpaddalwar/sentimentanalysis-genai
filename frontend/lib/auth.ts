const TOKEN_KEY = "csa_session_token";

export async function login(
  username: string,
  password: string
): Promise<boolean> {
  try {
    const response = await fetch(
      "/api/auth/login",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username,
          password,
        }),
      }
    );

    if (!response.ok) {
      return false;
    }

    const data = await response.json();

    if (!data?.token) {
      return false;
    }

    localStorage.setItem(
      TOKEN_KEY,
      data.token
    );

    return true;
  } catch {
    return false;
  }
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function isAuthenticated(): Promise<boolean> {
  const token = localStorage.getItem(TOKEN_KEY);

  if (!token) {
    return false;
  }

  try {
    const response = await fetch(
      "/api/auth/verify",
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      }
    );

    if (!response.ok) {
      logout();
      return false;
    }

    return true;
  } catch {
    logout();
    return false;
  }
}

export function getSessionToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}