const TOKEN_KEY = "csa_session_token";

export function login(username: string, password: string): boolean {
  const validUser = process.env.NEXT_PUBLIC_APP_USERNAME;
  const validPass = process.env.NEXT_PUBLIC_APP_PASSWORD;

  if (username === validUser && password === validPass) {
    const token = btoa(`${username}:${Date.now()}`);
    if (typeof window !== "undefined") {
      localStorage.setItem(TOKEN_KEY, token);
    }
    return true;
  }
  return false;
}

export function logout(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem(TOKEN_KEY);
}