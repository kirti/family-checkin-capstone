// auth-guard.js
// Include this as the FIRST script in <head> on any page that requires
// login. Redirects to login.html immediately if no token is stored.

(function () {
  const token = localStorage.getItem("authToken");
  if (!token) {
    window.location.href = "login.html";
  }
})();

function authHeader() {
  return { "Authorization": "Bearer " + localStorage.getItem("authToken") };
}

// Call this after any fetch to a protected endpoint. If the backend
// rejected the token (expired/invalid), this clears it and sends the
// person back to login instead of showing a confusing error.
function handleAuthError(status) {
  if (status === 401) {
    localStorage.removeItem("authToken");
    window.location.href = "login.html";
    return true;
  }
  return false;
}

function logout() {
  localStorage.removeItem("authToken");
  window.location.href = "login.html";
}
