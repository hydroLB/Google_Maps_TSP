"use client";

import { useRef, useState } from "react";

type TravelMode = "driving" | "walking" | "bicycling" | "transit";
type Metric = "time" | "distance";
type EndpointMode = "any-stop" | "destination" | "round-trip";
type Landmark = { name: string; shortName: string; latitude: number; longitude: number; aliases: string[] };
type RouteResult = { order: Landmark[]; total: number };

const landmarks: Landmark[] = [
  { name: "Grand Central Terminal, 89 E 42nd St, New York, NY 10017", shortName: "Grand Central Terminal", latitude: 40.752726, longitude: -73.977229, aliases: ["Grand Central Terminal", "Grand Central"] },
  { name: "Empire State Building, 20 W 34th St, New York, NY 10001", shortName: "Empire State Building", latitude: 40.748441, longitude: -73.985664, aliases: ["Empire State Building"] },
  { name: "Flatiron Building, 175 5th Ave, New York, NY 10010", shortName: "Flatiron Building", latitude: 40.741061, longitude: -73.989699, aliases: ["Flatiron Building"] },
  { name: "Washington Square Park, Washington Square, New York, NY 10012", shortName: "Washington Square Park", latitude: 40.730823, longitude: -73.997332, aliases: ["Washington Square Park"] },
  { name: "Brooklyn Bridge, New York, NY 10038", shortName: "Brooklyn Bridge", latitude: 40.706086, longitude: -73.996864, aliases: ["Brooklyn Bridge"] },
  { name: "The Metropolitan Museum of Art, 1000 5th Ave, New York, NY 10028", shortName: "The Met", latitude: 40.779437, longitude: -73.963244, aliases: ["Metropolitan Museum of Art", "The Met"] },
  { name: "Rockefeller Center, 45 Rockefeller Plaza, New York, NY 10111", shortName: "Rockefeller Center", latitude: 40.75874, longitude: -73.978674, aliases: ["Rockefeller Center"] },
  { name: "Central Park, New York, NY 10024", shortName: "Central Park", latitude: 40.781219, longitude: -73.966513, aliases: ["Central Park"] },
  { name: "Union Square, New York, NY 10003", shortName: "Union Square", latitude: 40.735863, longitude: -73.991084, aliases: ["Union Square"] },
];

const initialStart = landmarks[0].name;
const initialStops = [landmarks[1].name, landmarks[2].name, landmarks[3].name, "", "", "", ""];
const initialEnd = landmarks[4].name;
const factors: Record<TravelMode, number> = { driving: 1.28, walking: 1.18, bicycling: 1.22, transit: 1.32 };
const speeds: Record<TravelMode, number> = { driving: 24, walking: 4.8, bicycling: 15, transit: 19 };
const modeLabels: Record<TravelMode, string> = { driving: "Drive", walking: "Walk", bicycling: "Bike", transit: "Transit" };

function resolveLandmark(value: string) {
  const needle = value.trim().toLowerCase();
  return landmarks.find((item) => [item.name, item.shortName, ...item.aliases].some((candidate) => candidate.toLowerCase() === needle));
}

function distanceKm(a: Landmark, b: Landmark, mode: TravelMode) {
  const rad = (value: number) => value * Math.PI / 180;
  const lat1 = rad(a.latitude);
  const lat2 = rad(b.latitude);
  const dLat = lat2 - lat1;
  const dLon = rad(b.longitude - a.longitude);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 6371.0088 * 2 * Math.asin(Math.sqrt(h)) * factors[mode];
}

function edgeCost(a: Landmark, b: Landmark, mode: TravelMode, metric: Metric) {
  const km = distanceKm(a, b, mode);
  return metric === "distance" ? km : km / speeds[mode] * 60;
}

function routeTotal(order: Landmark[], mode: TravelMode, metric: Metric, endpointMode: EndpointMode) {
  let total = order.slice(0, -1).reduce((sum, item, index) => sum + edgeCost(item, order[index + 1], mode, metric), 0);
  if (endpointMode === "round-trip" && order.length > 1) total += edgeCost(order.at(-1)!, order[0], mode, metric);
  return total;
}

function permutations<T>(items: T[]): T[][] {
  if (items.length < 2) return [items];
  return items.flatMap((item, index) => permutations([...items.slice(0, index), ...items.slice(index + 1)]).map((rest) => [item, ...rest]));
}

function optimizeOrder(start: Landmark | undefined, stops: Landmark[], end: Landmark | undefined, mode: TravelMode, metric: Metric, endpointMode: EndpointMode): RouteResult {
  let best: RouteResult = { order: [], total: Infinity };
  for (const candidate of permutations(stops)) {
    const order = [...(start ? [start] : []), ...candidate, ...(endpointMode === "destination" && end ? [end] : [])];
    const total = routeTotal(order, mode, metric, endpointMode);
    if (total < best.total) best = { order, total };
  }
  return best;
}

function Segmented<T extends string>({ label, value, values, labels, disabled, onChange }: { label: string; value: T; values: readonly T[]; labels: Record<T, string>; disabled?: boolean; onChange: (value: T) => void }) {
  return <fieldset className="setting-row"><legend>{label}</legend><div className="segmented">{values.map((option) => <button type="button" key={option} className={value === option ? "selected" : ""} aria-pressed={value === option} disabled={disabled} onClick={() => onChange(option)}>{labels[option]}</button>)}</div></fieldset>;
}

export default function Home() {
  const [start, setStart] = useState(initialStart);
  const [stops, setStops] = useState(initialStops);
  const [end, setEnd] = useState(initialEnd);
  const [visibleStops, setVisibleStops] = useState(3);
  const [mode, setMode] = useState<TravelMode>("driving");
  const [metric, setMetric] = useState<Metric>("time");
  const [endpointMode, setEndpointMode] = useState<EndpointMode>("destination");
  const [status, setStatus] = useState<"Ready" | "Optimizing" | "Check input" | "Cancelled">("Ready");
  const [result, setResult] = useState<RouteResult>({ order: landmarks.slice(0, 5), total: 19 });
  const [resultOptions, setResultOptions] = useState<{ mode: TravelMode; metric: Metric; endpointMode: EndpointMode }>({ mode: "driving", metric: "time", endpointMode: "destination" });
  const [working, setWorking] = useState(false);
  const [hasResult, setHasResult] = useState(false);
  const [guidedOpen, setGuidedOpen] = useState(false);
  const [guidedValue, setGuidedValue] = useState(initialStops.slice(0, 3).join("\n"));
  const [copied, setCopied] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<Landmark | null>(null);
  const [geoStatus, setGeoStatus] = useState<"idle" | "locating" | "active" | "denied">("idle");
  const jobRef = useRef<number | null>(null);
  const activeStops = stops.slice(0, visibleStops);
  const filledStops = activeStops.filter((value) => value.trim()).length;
  const timeTotal = hasResult ? routeTotal(result.order, resultOptions.mode, "time", resultOptions.endpointMode) : 0;
  const distanceTotal = hasResult ? routeTotal(result.order, resultOptions.mode, "distance", resultOptions.endpointMode) : 0;

  function resolveValue(value: string) {
    return value.trim().toLowerCase() === "current location" && currentLocation ? currentLocation : resolveLandmark(value);
  }

  function setStop(index: number, value: string) {
    setStops((current) => current.map((item, itemIndex) => itemIndex === index ? value : item));
  }

  function moveStop(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= visibleStops) return;
    setStops((current) => {
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function removeStop(index: number) {
    if (visibleStops <= 3) {
      setStop(index, "");
      return;
    }
    setStops((current) => [...current.slice(0, index), ...current.slice(index + 1), ""].slice(0, 7));
    setVisibleStops((count) => count - 1);
  }

  function optimize() {
    if (working) return;
    const resolvedStops = activeStops.map(resolveValue);
    const resolvedStart = start.trim() ? resolveValue(start) : undefined;
    const resolvedEnd = end.trim() ? resolveValue(end) : undefined;
    if (filledStops < 3 || resolvedStops.some((item) => !item) || (start.trim() && !resolvedStart) || (endpointMode === "destination" && !resolvedEnd)) {
      setStatus("Check input");
      setHasResult(false);
      return;
    }
    setWorking(true);
    setStatus("Optimizing");
    jobRef.current = window.setTimeout(() => {
      setResult(optimizeOrder(resolvedStart, resolvedStops as Landmark[], resolvedEnd, mode, metric, endpointMode));
      setResultOptions({ mode, metric, endpointMode });
      setStatus("Ready");
      setHasResult(true);
      setWorking(false);
      jobRef.current = null;
    }, 480);
  }

  function cancel() {
    if (jobRef.current !== null) window.clearTimeout(jobRef.current);
    jobRef.current = null;
    setWorking(false);
    setStatus("Cancelled");
  }

  function applyGuidedEntry() {
    const values = guidedValue.split(/\r?\n/).map((value) => value.trim()).filter(Boolean).slice(0, 7);
    setStops(Array.from({ length: 7 }, (_, index) => values[index] ?? ""));
    setVisibleStops(Math.max(3, values.length));
    setGuidedOpen(false);
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setGeoStatus("denied");
      return;
    }
    setGeoStatus("locating");
    navigator.geolocation.getCurrentPosition(({ coords }) => {
      const location: Landmark = {
        name: `${coords.latitude.toFixed(6)},${coords.longitude.toFixed(6)}`,
        shortName: "Current location",
        latitude: coords.latitude,
        longitude: coords.longitude,
        aliases: ["Current location"],
      };
      setCurrentLocation(location);
      setStart("Current location");
      setGeoStatus("active");
    }, () => setGeoStatus("denied"), { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
  }

  const routeValues = hasResult ? result.order.map((item) => item.name) : [];
  if (resultOptions.endpointMode === "round-trip" && hasResult && result.order.length) routeValues.push(result.order[0].name);
  const mapsUrl = `https://www.google.com/maps/dir/${routeValues.map(encodeURIComponent).join("/")}`;

  function exportCsv() {
    const csv = ["position,address", ...routeValues.map((address, index) => `${index + 1},"${address.replaceAll('"', '""')}"`)].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "optimized-route.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function copyRoute() {
    await navigator.clipboard.writeText(mapsUrl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return <main className="app-shell">
    <nav className="topbar" aria-label="Application">
      <div className="brand-mark" aria-hidden="true"><span>1</span><span>2</span><i /></div>
      <strong>Fastest Route Optimizer</strong>
      <span className="demo-label">NYC · DEMO</span>
      <span className="sr-only" aria-live="polite">{status}</span>
    </nav>

    <div className="workspace">
      <section className="planner-pane" aria-labelledby="planner-title">
        <header className="section-header"><div><span className="eyebrow">Demo - NYC Landmarks</span><h1 id="planner-title">Stops ({filledStops}/{visibleStops} filled, min 3, max 7)</h1></div><button type="button" className="text-button" onClick={() => setGuidedOpen(true)}>Guided Entry</button></header>
        <datalist id="landmarks">{landmarks.map((item) => <option value={item.name} key={item.name} />)}</datalist>
        <section className="ios-group route-editor" aria-label="Route stops">
          <div className="location-row endpoint-row"><span className="location-marker start-marker" aria-hidden="true" /><div className="location-field"><label htmlFor="start">Start</label><input id="start" list="landmarks" value={start} onChange={(event) => setStart(event.target.value)} placeholder="Optional starting point" /></div><button type="button" className={`locate-button ${geoStatus}`} onClick={useCurrentLocation} aria-label="Use current location" title={geoStatus === "denied" ? "Location unavailable" : "Use current location"}>{geoStatus === "locating" ? <span className="spinner" /> : "⌖"}</button></div>
          {activeStops.map((value, index) => <div className="location-row" key={index}>
            <span className="location-marker stop-marker" aria-hidden="true">{index + 1}</span>
            <div className="location-field"><label htmlFor={`stop-${index}`}>Stop {index + 1}</label><input id={`stop-${index}`} list="landmarks" value={value} onChange={(event) => setStop(index, event.target.value)} placeholder="Choose a landmark" /></div>
            <div className="row-actions"><button type="button" aria-label={`Move stop ${index + 1} up`} onClick={() => moveStop(index, -1)} disabled={index === 0}>↑</button><button type="button" aria-label={`Move stop ${index + 1} down`} onClick={() => moveStop(index, 1)} disabled={index === visibleStops - 1}>↓</button><button type="button" className="remove" aria-label={`Delete stop ${index + 1}`} onClick={() => removeStop(index)}>−</button></div>
          </div>)}
          <button type="button" className="add-row" onClick={() => setVisibleStops((count) => Math.min(7, count + 1))} disabled={visibleStops === 7}><span>＋</span>Add stop <small>{filledStops}/7</small></button>
          <div className={`location-row endpoint-row ${endpointMode !== "destination" ? "disabled-row" : ""}`}><span className="location-marker end-marker" aria-hidden="true" /><div className="location-field"><label htmlFor="end">Destination</label><input id="end" list="landmarks" value={endpointMode === "round-trip" ? start : endpointMode === "any-stop" ? "" : end} disabled={endpointMode !== "destination"} required={endpointMode === "destination"} aria-invalid={endpointMode === "destination" && !resolveLandmark(end)} onChange={(event) => setEnd(event.target.value)} placeholder={endpointMode === "any-stop" ? "Whichever stop is fastest" : "Required finish"} /></div>{endpointMode === "destination" && <span className={`input-state ${!resolveLandmark(end) ? "invalid" : ""}`} />}</div>
        </section>

        <h2 className="options-title">Routing options</h2>
        <section className="ios-group settings-group" aria-label="Route options">
          <Segmented label="Travel mode" value={mode} values={["driving", "walking", "bicycling", "transit"]} labels={modeLabels} disabled={working} onChange={setMode} />
          <Segmented label="Optimize for" value={metric} values={["time", "distance"]} labels={{ time: "Time", distance: "Distance" }} disabled={working} onChange={setMetric} />
          <Segmented label="Trip type" value={endpointMode} values={["any-stop", "destination", "round-trip"]} labels={{ "any-stop": "Any stop", destination: "Destination", "round-trip": "Back to start" }} disabled={working} onChange={setEndpointMode} />
        </section>
        <div className="primary-actions"><button type="button" className="optimize-button" onClick={optimize} disabled={working}>{working ? <><span className="spinner" />Optimizing</> : <>Optimize route <span>›</span></>}</button>{working && <button type="button" className="cancel-button" onClick={cancel}>Cancel</button>}</div>
      </section>

      <aside className="result-pane" aria-labelledby="route-title">
        <header className="result-header"><div><span className="eyebrow">Optimized route</span><h2 id="route-title">{resultOptions.metric === "time" ? "Fastest route" : "Shortest route"}</h2></div></header>
        {hasResult ? <>
          <div className="metric-grid"><article className={resultOptions.metric === "time" ? "featured" : ""}><span>Estimated time</span><strong>{Math.max(1, Math.round(timeTotal))}<small> min</small></strong></article><article className={resultOptions.metric === "distance" ? "featured" : ""}><span>Estimated distance</span><strong>{distanceTotal.toFixed(1)}<small> km</small></strong></article></div>
          <div className="route-card"><div className="route-meta"><span>{modeLabels[resultOptions.mode]}</span><i /><span>{resultOptions.endpointMode === "round-trip" ? "Back to start" : resultOptions.endpointMode === "destination" ? "Set destination" : "Best finish"}</span><i /><span>{result.order.length} places</span></div><ol className="timeline">
            {result.order.map((place, index) => {
              const final = index === result.order.length - 1;
              const type = index === 0 ? "Start" : final && resultOptions.endpointMode === "destination" ? "Destination" : final && resultOptions.endpointMode === "any-stop" ? "Finish" : `Stop ${index}`;
              return <li key={`${place.name}-${index}`}><span className={`timeline-marker ${index === 0 ? "first" : final && resultOptions.endpointMode !== "round-trip" ? "last" : ""}`}>{index === 0 ? "●" : index}</span><div><small>{type}</small><strong>{place.shortName}</strong><p>{place.shortName === "Current location" ? "Device position" : place.name.replace(`${place.shortName}, `, "")}</p></div></li>;
            })}
            {resultOptions.endpointMode === "round-trip" && result.order.length > 0 && <li><span className="timeline-marker last">↩</span><div><small>Return</small><strong>{result.order[0].shortName}</strong><p>Back to your starting point</p></div></li>}
          </ol></div>
          <p className="model-note">Demo estimates use landmark distances and fixed travel speeds, without street routing or live traffic. Check the route in Maps before traveling.</p>
          <div className="result-actions"><a className="maps-button" href={mapsUrl} target="_blank" rel="noreferrer">Open in Maps <span>↗</span></a><button type="button" onClick={copyRoute}>{copied ? "Copied" : "Copy link"}</button><button type="button" onClick={exportCsv}>Export</button></div>
        </> : <div className="empty-result" role="status"><h3>{status === "Check input" ? "Check your stops" : "No route has been generated yet."}</h3><p>{status === "Check input" ? "Choose a suggested landmark for every stop, then optimize again." : "Add your stops and click Optimize Route."}</p></div>}
      </aside>
    </div>

    {guidedOpen && <div className="sheet-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setGuidedOpen(false); }}><section className="sheet" role="dialog" aria-modal="true" aria-labelledby="guided-title"><div className="sheet-handle" /><header><button type="button" onClick={() => setGuidedOpen(false)}>Cancel</button><h2 id="guided-title">Paste stops</h2><button type="button" className="done" onClick={applyGuidedEntry}>Done</button></header><label htmlFor="guided-stops">One landmark per line</label><textarea id="guided-stops" value={guidedValue} onChange={(event) => setGuidedValue(event.target.value)} autoFocus /><p>Up to seven stops. Start and destination stay unchanged.</p></section></div>}
  </main>;
}
