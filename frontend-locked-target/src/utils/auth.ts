/* eslint-disable @typescript-eslint/no-unused-vars */
// src/utils/auth.ts
export const checkSession = async (): Promise<boolean> => {
    try {
      const res = await fetch("http://localhost:5000/me/", {
        credentials: "include", // send cookie
      });
      return res.ok;
    } catch (err) {
      return false;
    }
  };
  