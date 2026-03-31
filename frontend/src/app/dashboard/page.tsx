import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card } from "@/components/ui/Card";

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  const stats = [
    { label: "Total Videos", value: "0" },
    { label: "Total Clips", value: "0" },
    { label: "Exports This Month", value: "0" },
  ];

  return (
    <DashboardLayout title="Dashboard">
      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <p className="text-slate-400 text-sm font-medium">{stat.label}</p>
            <p className="text-3xl font-bold text-white mt-1">{stat.value}</p>
          </Card>
        ))}
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <div className="relative group">
          <button
            disabled
            className="w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl
                       border-2 border-dashed border-slate-700 text-slate-500 cursor-not-allowed
                       bg-[#1E293B]/50 transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M17 8L12 3L7 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M12 3V15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Upload Video
          </button>
          <span className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-slate-700 text-slate-300
                           text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
            Coming in Prompt 2
          </span>
        </div>

        <div className="relative group">
          <button
            disabled
            className="w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl
                       border-2 border-dashed border-slate-700 text-slate-500 cursor-not-allowed
                       bg-[#1E293B]/50 transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.54 6.42C22.4212 5.94541 22.1793 5.51057 21.8387 5.15941C21.498 4.80824 21.0708 4.55318 20.6 4.42C18.88 4 12 4 12 4C12 4 5.12 4 3.4 4.46C2.92925 4.59318 2.50198 4.84824 2.16135 5.19941C1.82072 5.55057 1.57879 5.98541 1.46 6.46C1.14521 8.20556 0.991235 9.97631 1 11.75C0.988787 13.537 1.14277 15.3213 1.46 17.08C1.59096 17.5398 1.83831 17.9581 2.17814 18.2945C2.51798 18.6308 2.93882 18.8738 3.4 19C5.12 19.46 12 19.46 12 19.46C12 19.46 18.88 19.46 20.6 19C21.0708 18.8668 21.498 18.6118 21.8387 18.2606C22.1793 17.9094 22.4212 17.4746 22.54 17C22.8524 15.2676 23.0063 13.5103 23 11.75C23.0112 9.96295 22.8573 8.1787 22.54 6.42Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M9.75 15.02L15.5 11.75L9.75 8.48V15.02Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Import from YouTube
          </button>
          <span className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-slate-700 text-slate-300
                           text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
            Coming in Prompt 2
          </span>
        </div>
      </div>

      {/* Recent videos */}
      <Card>
        <h2 className="text-base font-semibold text-white mb-4">Recent Videos</h2>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="2" y="2" width="20" height="20" rx="3" stroke="#475569" strokeWidth="2"/>
              <path d="M10 8L16 12L10 16V8Z" fill="#475569"/>
            </svg>
          </div>
          <p className="text-slate-400 font-medium">No videos yet</p>
          <p className="text-slate-600 text-sm mt-1">Upload a video or import from YouTube to get started</p>
        </div>
      </Card>
    </DashboardLayout>
  );
}
