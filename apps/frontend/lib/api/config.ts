export const API_URL = process.env.NEXT_PUBLIC_API_URL === undefined
  ? 'http://127.0.0.1:8000'
  : process.env.NEXT_PUBLIC_API_URL;
