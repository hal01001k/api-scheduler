"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Clock,
  Plus,
  Target as TargetIcon,
  Calendar,
  Play,
  Pause,
  ChevronRight,
  ShieldCheck,
  Zap,
  RotateCcw
} from "lucide-react";
import { cn } from "./lib/utils";
import { Modal } from "./components/Modal";
import type { Target, Schedule, Run, MetricAggregate, Method } from "./lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<"overview" | "targets" | "schedules">("overview");
  const [metrics, setMetrics] = useState<MetricAggregate | null>(null);
  const [recentRuns, setRecentRuns] = useState<Run[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Modal states
  const [isTargetModalOpen, setIsTargetModalOpen] = useState(false);
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);

  // Form states
  const [newTarget, setNewTarget] = useState({ name: "", url: "", method: "GET" as Method, headers: "{}" });
  const [newSchedule, setNewSchedule] = useState({ name: "", target_id: "", type: "interval", value: "" });

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [mRes, rRes, tRes, sRes] = await Promise.all([
        fetch(`${API_URL}/metrics`),
        fetch(`${API_URL}/runs?limit=10`),
        fetch(`${API_URL}/targets`),
        fetch(`${API_URL}/schedules`)
      ]);

      if (mRes.ok) setMetrics(await mRes.json());
      if (rRes.ok) setRecentRuns(await rRes.json());
      if (tRes.ok) setTargets(await tRes.json());
      if (sRes.ok) setSchedules(await sRes.json());
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  const handleCreateTarget = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const headers = JSON.parse(newTarget.headers);
      const res = await fetch(`${API_URL}/targets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...newTarget, headers })
      });
      if (res.ok) {
        setIsTargetModalOpen(false);
        setNewTarget({ name: "", url: "", method: "GET", headers: "{}" });
        fetchData();
      }
    } catch (err) {
      alert("Invalid headers JSON or failed to create target");
    }
  };

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_URL}/schedules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...newSchedule,
          target_id: parseInt(newSchedule.target_id),
          duration_seconds: null
        })
      });
      if (res.ok) {
        setIsScheduleModalOpen(false);
        setNewSchedule({ name: "", target_id: "", type: "interval", value: "" });
        fetchData();
      }
    } catch (err) {
      alert("Failed to create schedule");
    }
  };

  const handlePauseResume = async (id: number, currentStatus: string) => {
    const action = currentStatus === "active" ? "pause" : "resume";
    try {
      await fetch(`${API_URL}/schedules/${id}/${action}`, { method: "POST" });
      fetchData();
    } catch (err) {
      console.error(`Failed to ${action} schedule:`, err);
    }
  };

  return (
    <div className="flex min-h-screen bg-transparent">
      {/* Sidebar */}
      <aside className="w-64 border-r border-white/5 p-6 flex flex-col gap-8">
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Zap className="text-white" size={20} />
          </div>
          <span className="font-bold text-xl tracking-tight">SkyGate</span>
        </div>

        <nav className="flex flex-col gap-1">
          {[
            { id: "overview", label: "Overview", icon: Activity },
            { id: "targets", label: "Targets", icon: TargetIcon },
            { id: "schedules", label: "Schedules", icon: Clock },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all text-sm font-medium",
                activeTab === tab.id
                  ? "bg-blue-600/10 text-blue-400 shadow-sm"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              )}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="mt-auto flex flex-col gap-3">
          <button onClick={() => setIsTargetModalOpen(true)} className="btn-primary w-full justify-center">
            <Plus size={18} />
            New Target
          </button>
          <button onClick={() => setIsScheduleModalOpen(true)} className="flex items-center justify-center gap-2 w-full px-3 py-2.5 rounded-xl border border-white/5 bg-white/5 text-sm font-medium text-gray-300 hover:bg-white/10 hover:text-white transition-all">
            <Calendar size={18} />
            New Schedule
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-y-auto max-w-7xl mx-auto w-full">
        <header className="mb-10 flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-2 capitalize">{activeTab}</h1>
            <p className="text-gray-400 text-sm">Monitor and manage your API automation.</p>
          </div>
          <div className="text-xs font-mono text-gray-500 bg-white/5 px-3 py-1.5 rounded-full border border-white/5">
            Status: <span className="text-emerald-500">Connected</span>
          </div>
        </header>

        <div className="animate-fade-in">
          {activeTab === "overview" && (
            <div className="space-y-8">
              {/* Metrics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <MetricCard
                  label="Total Runs"
                  value={metrics?.total_runs.toString() || "0"}
                  icon={Activity}
                  color="bg-blue-500/10 text-blue-500"
                />
                <MetricCard
                  label="Success Rate"
                  value={`${metrics?.success_rate.toFixed(1) || "0"}%`}
                  icon={ShieldCheck}
                  color="bg-emerald-500/10 text-emerald-500"
                />
                <MetricCard
                  label="Avg Latency"
                  value={`${metrics?.avg_latency_ms.toFixed(0) || "0"}ms`}
                  icon={Zap}
                  color="bg-orange-500/10 text-orange-500"
                />
              </div>

              {/* Recent Runs */}
              <div className="glass-card overflow-hidden">
                <div className="p-6 border-b border-white/5 flex items-center justify-between">
                  <h2 className="text-lg font-semibold italic text-gray-300">Live Execution Log</h2>
                  <button
                    onClick={fetchData}
                    className="p-2 text-gray-400 hover:text-white transition-colors bg-white/5 rounded-lg"
                  >
                    <RotateCcw size={16} className={isLoading ? "animate-spin" : ""} />
                  </button>
                </div>
                <div className="divide-y divide-white/5">
                  {recentRuns.length === 0 ? (
                    <div className="text-center py-16 text-gray-500 italic">No data streams detected...</div>
                  ) : (
                    recentRuns.map((run) => (
                      <div key={run.id} className="flex items-center justify-between p-5 hover:bg-white/[0.02] transition-colors group">
                        <div className="flex items-center gap-4">
                          <div className={cn(
                            "w-2.5 h-2.5 rounded-full",
                            run.status === "success" ? "bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.4)]" : "bg-red-500 shadow-[0_0_12px_rgba(239,68,68,0.4)]"
                          )} />
                          <div>
                            <div className="font-semibold text-sm">Execution <span className="text-gray-500">#{run.id}</span></div>
                            <div className="text-[11px] text-gray-500 uppercase tracking-wider mt-0.5">{new Date(run.started_at).toLocaleString()}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-12">
                          <div className="flex flex-col items-end">
                            <span className="text-xs text-gray-500 uppercase font-bold tracking-tighter">Latency</span>
                            <span className="text-sm font-mono text-blue-400">{run.latency_ms?.toFixed(0)} ms</span>
                          </div>
                          <div className={run.status === "success" ? "badge-success" : "badge-failure"}>
                            {run.status}
                          </div>
                          <ChevronRight size={16} className="text-gray-600 group-hover:text-gray-400 transition-colors" />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === "schedules" && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {schedules.map((schedule) => (
                <div key={schedule.id} className="glass-card p-6 relative group">
                  <div className="absolute top-4 right-4 capitalize">
                    <span className={cn(
                      "text-[10px] font-bold px-2 py-0.5 rounded-full border",
                      schedule.status === "active" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-white/5 text-gray-400 border-white/10"
                    )}>
                      {schedule.status}
                    </span>
                  </div>

                  <div className="flex items-start gap-4 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-500">
                      <Clock size={20} />
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-100">{schedule.name}</h3>
                      <p className="text-xs text-gray-500 font-mono mt-1">
                        {schedule.type === "interval" ? `Intvl: ${schedule.value}s` : `Cron: ${schedule.value}`}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between border-t border-white/5 pt-4">
                    <div className="text-[10px] text-gray-500 uppercase font-bold tracking-widest">Toggle Status</div>
                    <button
                      onClick={() => handlePauseResume(schedule.id, schedule.status)}
                      className={cn(
                        "p-2.5 rounded-xl transition-all",
                        schedule.status === "active"
                          ? "bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20"
                          : "bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white"
                      )}
                    >
                      {schedule.status === "active" ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}
                    </button>
                  </div>
                </div>
              ))}
              {schedules.length === 0 && (
                <div className="col-span-full py-20 text-center border-2 border-dashed border-white/5 rounded-3xl">
                  <p className="text-gray-500 italic">No schedules configured yet.</p>
                </div>
              )}
            </div>
          )}

          {activeTab === "targets" && (
            <div className="space-y-4">
              {targets.map((target) => (
                <div key={target.id} className="glass-card p-5 flex items-center justify-between group">
                  <div className="flex items-center gap-5">
                    <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 shadow-inner">
                      <TargetIcon size={24} />
                    </div>
                    <div>
                      <div className="font-bold text-gray-200">{target.name}</div>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-[10px] font-bold uppercase py-0.5 px-2 bg-blue-500/20 text-blue-400 rounded-md tracking-tighter border border-blue-500/20">{target.method}</span>
                        <span className="text-xs font-mono text-gray-500 truncate max-w-sm">{target.url}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-[10px] text-gray-500 uppercase font-bold tracking-tighter mb-0.5">Complexity</div>
                      <div className="text-xs font-mono text-white/60">
                        {Object.keys(target.headers).length} Headers
                      </div>
                    </div>
                    <button className="p-2 text-gray-600 hover:text-gray-300 transition-colors opacity-0 group-hover:opacity-100">
                      <ChevronRight size={20} />
                    </button>
                  </div>
                </div>
              ))}
              {targets.length === 0 && (
                <div className="py-20 text-center border-2 border-dashed border-white/5 rounded-3xl">
                  <p className="text-gray-500 italic">No target environments mapped.</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modals */}
        <TargetModal
          isOpen={isTargetModalOpen}
          onClose={() => setIsTargetModalOpen(false)}
          onSubmit={handleCreateTarget}
          newTarget={newTarget}
          setNewTarget={setNewTarget}
        />

        <ScheduleModal
          isOpen={isScheduleModalOpen}
          onClose={() => setIsScheduleModalOpen(false)}
          onSubmit={handleCreateSchedule}
          newSchedule={newSchedule}
          setNewSchedule={setNewSchedule}
          targets={targets}
        />
      </main>
    </div>
  );
}

function MetricCard({ label, value, icon: Icon, color }: any) {
  return (
    <div className="glass-card p-6 flex items-center gap-6">
      <div className={cn("w-14 h-14 rounded-2xl flex items-center justify-center shadow-inner", color)}>
        <Icon size={28} />
      </div>
      <div>
        <p className="text-[11px] text-gray-500 uppercase font-bold tracking-widest mb-1">{label}</p>
        <p className="text-3xl font-black tracking-tight text-white">{value}</p>
      </div>
    </div>
  );
}

function TargetModal({ isOpen, onClose, onSubmit, newTarget, setNewTarget }: any) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Map New Target">
      <form onSubmit={onSubmit} className="space-y-5">
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Target Alias</label>
          <input
            required
            className="input-field"
            value={newTarget.name}
            onChange={e => setNewTarget({ ...newTarget, name: e.target.value })}
            placeholder="e.g. Production Cluster"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Endpoint URL</label>
          <input
            required
            type="url"
            className="input-field font-mono text-sm"
            value={newTarget.url}
            onChange={e => setNewTarget({ ...newTarget, url: e.target.value })}
            placeholder="https://api.example.com/v1"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">HTTP Method</label>
          <select
            className="input-field"
            value={newTarget.method}
            onChange={e => setNewTarget({ ...newTarget, method: e.target.value as Method })}
          >
            {["GET", "POST", "PUT", "DELETE", "PATCH"].map(m => (
              <option key={m} value={m} className="bg-neutral-900">{m}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Request Headers (JSON)</label>
          <textarea
            className="input-field font-mono text-xs h-32"
            value={newTarget.headers}
            onChange={e => setNewTarget({ ...newTarget, headers: e.target.value })}
            placeholder='{ "Authorization": "Bearer token" }'
          />
        </div>
        <button type="submit" className="btn-primary w-full justify-center py-4 text-sm mt-4">
          Initialize Target
        </button>
      </form>
    </Modal>
  );
}

function ScheduleModal({ isOpen, onClose, onSubmit, newSchedule, setNewSchedule, targets }: any) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Configure Schedule">
      <form onSubmit={onSubmit} className="space-y-5">
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Profile Name</label>
          <input
            required
            className="input-field"
            value={newSchedule.name}
            onChange={e => setNewSchedule({ ...newSchedule, name: e.target.value })}
            placeholder="e.g. Health Monitor"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Linked Target</label>
          <select
            required
            className="input-field"
            value={newSchedule.target_id}
            onChange={e => setNewSchedule({ ...newSchedule, target_id: e.target.value })}
          >
            <option value="" className="bg-neutral-900 text-gray-500">Select target environment...</option>
            {targets.map((t: any) => (
              <option key={t.id} value={t.id} className="bg-neutral-900">{t.name}</option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Execution Type</label>
            <select
              className="input-field"
              value={newSchedule.type}
              onChange={e => setNewSchedule({ ...newSchedule, type: e.target.value })}
            >
              <option value="interval" className="bg-neutral-900">Interval</option>
              <option value="cron" className="bg-neutral-900">Cron</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Expression</label>
            <input
              required
              className="input-field"
              value={newSchedule.value}
              onChange={e => setNewSchedule({ ...newSchedule, value: e.target.value })}
              placeholder={newSchedule.type === "interval" ? "60 (s)" : "* * * * *"}
            />
          </div>
        </div>
        <button type="submit" className="btn-primary w-full justify-center py-4 text-sm mt-4">
          Deploy Schedule
        </button>
      </form>
    </Modal>
  );
}
