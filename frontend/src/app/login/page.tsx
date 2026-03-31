import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-[#0F172A] px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-2">
            <div className="w-8 h-8 rounded-lg bg-[#7C3AED] flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M5 3L19 12L5 21V3Z" fill="white" />
              </svg>
            </div>
            <span className="text-2xl font-bold tracking-tight text-white">ClipBandit</span>
          </div>
          <p className="text-slate-400 text-sm">AI-powered video clipping for creators</p>
        </div>

        <LoginForm />
      </div>
    </main>
  );
}
