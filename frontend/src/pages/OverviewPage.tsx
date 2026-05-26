import { useEffect, useMemo, useState } from "react";
import { listAlarms, listDevices } from "../api/client";
import type { Alarm, Device } from "../types";

export function OverviewPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [error, setError] = useState<string>();

  async function refresh() {
    setError(undefined);
    try {
      const [deviceData, alarmData] = await Promise.all([listDevices(), listAlarms()]);
      setDevices(deviceData);
      setAlarms(alarmData);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "加载概览失败");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const offlineCount = useMemo(() => devices.filter((device) => device.status !== "online").length, [devices]);
  const openAlarmCount = useMemo(() => alarms.filter((alarm) => alarm.status === "open").length, [alarms]);

  return (
    <main className="page-grid">
      <section className="card full-span">
        <div className="section-header">
          <div>
            <p className="eyebrow">Security Overview</p>
            <h2>设备与告警概览</h2>
          </div>
          <button type="button" onClick={() => void refresh()}>
            刷新
          </button>
        </div>
        {error ? <div className="error-banner">{error}</div> : null}
        <div className="metric-grid">
          <div className="metric-card">
            <span>设备总数</span>
            <strong>{devices.length}</strong>
          </div>
          <div className="metric-card danger">
            <span>异常设备</span>
            <strong>{offlineCount}</strong>
          </div>
          <div className="metric-card">
            <span>告警总数</span>
            <strong>{alarms.length}</strong>
          </div>
          <div className="metric-card danger">
            <span>未关闭告警</span>
            <strong>{openAlarmCount}</strong>
          </div>
        </div>
      </section>

      <section className="card">
        <h3>设备列表</h3>
        <div className="stack">
          {devices.map((device) => (
            <article className="asset-row" key={device.id}>
              <strong>{device.name}</strong>
              <span>{device.status}</span>
              <p>{device.location} · {device.ip ?? "IP 未知"}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>告警列表</h3>
        <div className="stack">
          {alarms.map((alarm) => (
            <article className="asset-row" key={alarm.id}>
              <strong>{alarm.summary}</strong>
              <span>{alarm.severity}</span>
              <p>{alarm.status} · {alarm.occurred_at}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
