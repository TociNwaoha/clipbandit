const INTERNAL_API_URL = process.env.INTERNAL_API_URL;
const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;

export const SERVER_API_URL = INTERNAL_API_URL || PUBLIC_API_URL || "http://backend:8000";
