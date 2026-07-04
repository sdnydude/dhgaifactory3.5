import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import Link from '@docusaurus/Link';
import styles from './patchbay.module.css';
import {
  racks, tapes, offsite, suggestions, LAN, TS,
  type Module, type Tape,
} from './services';

type StatusMap = Record<string, 'up' | 'down'>;
interface Citation { title?: string; project: string; source_file: string; url?: string; }

const GREETING =
  'Talkback live. Ask about anything on the board — answers cite their sources by lighting up the racks.';

function moduleState(mod: Module, status: StatusMap | null): 'on' | 'warn' | 'off' | 'unknown' {
  if (mod.statusKey && status && mod.statusKey in status) {
    return status[mod.statusKey] === 'up' ? 'on' : 'off';
  }
  if (mod.staticState) return mod.staticState;
  return 'unknown';
}

function matchesQuery(text: string, q: string): boolean {
  return q === '' || text.toLowerCase().includes(q);
}

export default function Patchbay(): React.ReactElement {
  const [mounted, setMounted] = useState(false);
  const [status, setStatus] = useState<StatusMap | null>(null);
  const [apiOffline, setApiOffline] = useState(false);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(GREETING);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [citedProjects, setCitedProjects] = useState<Set<string>>(new Set());
  const [streaming, setStreaming] = useState(false);
  const [asked, setAsked] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Live status + first-visit monitor state (client-only).
  useEffect(() => {
    setMounted(true);
    let cancelled = false;
    fetch('/api/patchbay/status')
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d) => { if (!cancelled) setStatus(d.services ?? {}); })
      .catch(() => { if (!cancelled) setApiOffline(true); });
    if (typeof window !== 'undefined' && localStorage.getItem('tb-closed') !== '1') {
      setOpen(true);
    }
    return () => { cancelled = true; };
  }, []);

  const q = query.trim().toLowerCase();

  const openMonitor = useCallback(() => {
    setOpen(true);
    if (typeof window !== 'undefined') localStorage.removeItem('tb-closed');
  }, []);
  const closeMonitor = useCallback(() => {
    setOpen(false);
    setCitedProjects(new Set());
    if (typeof window !== 'undefined') localStorage.setItem('tb-closed', '1');
  }, []);

  const ask = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;
    setAsked(true);
    openMonitor();
    setQuestion(trimmed);
    setAnswer('');
    setCitations([]);
    setCitedProjects(new Set());
    setStreaming(true);
    setQuery('');

    try {
      const resp = await fetch('/api/talkback', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: trimmed}),
      });
      if (!resp.ok || !resp.body) {
        throw new Error(resp.status === 429
          ? 'Too many questions — give it a minute and try again.'
          : 'talkback_unreachable');
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let acc = '';
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {stream: true});
        const frames = buffer.split('\n\n');
        buffer = frames.pop() ?? '';
        for (const frame of frames) {
          let event = 'message';
          let data = '';
          for (const line of frame.split('\n')) {
            if (line.startsWith('event: ')) event = line.slice(7);
            else if (line.startsWith('data: ')) data += line.slice(6);
          }
          if (!data) continue;
          const parsed = JSON.parse(data);
          if (event === 'citations') {
            setCitations(parsed.citations ?? []);
            setCitedProjects(new Set((parsed.citations ?? []).map((c: Citation) => c.project)));
          } else if (event === 'delta') {
            acc += parsed.text ?? '';
            setAnswer(acc);
          } else if (event === 'error') {
            setAnswer(parsed.message ?? 'Talkback is temporarily unavailable.');
          }
        }
      }
    } catch (e) {
      setAnswer(
        e instanceof Error && e.message && e.message !== 'talkback_unreachable'
          ? e.message
          : 'Talkback is offline right now — the board still works as a launchpad.',
      );
    } finally {
      setStreaming(false);
    }
  }, [openMonitor, streaming]);

  // Keyboard: "/" focuses the strip, Esc closes/clears.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement !== inputRef.current) {
        e.preventDefault();
        inputRef.current?.focus();
      } else if (e.key === 'Escape') {
        if (open) closeMonitor();
        setQuery('');
        inputRef.current?.blur();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, closeMonitor]);

  const modelLabel = 'qwen3:14b · local';
  const liveCount = useMemo(
    () => (status ? Object.values(status).filter((s) => s === 'up').length : null),
    [status],
  );

  const moduleHref = (mod: Module): string =>
    mod.tunnel ?? `${LAN}:${mod.port}${mod.path ?? ''}`;

  return (
    <div className={styles.frame}>
      <header className={styles.mast}>
        <span className={styles.mark}>DHG <em>Patchbay</em></span>
        <span className={styles.sub}>docs.digitalharmonyai.com — every signal in the building</span>
      </header>

      <div className={styles.cmd}>
        <div className={styles.cmdBox}>
          <span className={styles.prompt}>&gt;</span>
          <input
            ref={inputRef}
            type="text"
            aria-label="Filter services or ask Talkback"
            placeholder="patch into anything — type to filter, Enter to ask talkback"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && query.trim()) ask(query); }}
          />
          <span className={styles.kbd}>/</span>
        </div>
        <div className={`${styles.cmdHint} ${apiOffline ? styles.cmdHintDown : ''}`}>
          {apiOffline
            ? <><b>●</b> live status unavailable — links still work</>
            : liveCount === null
              ? <>connecting to the board…</>
              : <><b>●</b> {liveCount} signals live · type to filter · Enter to ask talkback</>}
        </div>

        {mounted && open && (
          <div className={styles.monitor}>
            <div className={styles.monHead}>
              <span className={styles.tbLed} />
              <h4>Talkback</h4>
              <span className={styles.monModel}>{modelLabel}</span>
              <button className={styles.monClose} onClick={closeMonitor} aria-label="Close talkback">ESC ✕</button>
            </div>
            {asked && <div className={styles.monQ}><b>&gt;</b> {question}</div>}
            <div className={styles.monA}>
              {answer}
              {streaming && <span className={styles.cursor} />}
            </div>
            {citations.length > 0 && (
              <div className={styles.monCites}>
                <span>PATCHED TO:</span>
                {citations.map((c) => (
                  c.url
                    ? <Link key={c.source_file} to={c.url}>{c.title ?? c.project}</Link>
                    : <span key={c.source_file}>{c.title ?? c.project}</span>
                ))}
              </div>
            )}
            {!asked && (
              <div className={styles.chips}>
                {suggestions.map((s) => (
                  <button key={s} onClick={() => ask(s)}>{s}</button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {racks.map((rack) => (
        <section className={styles.rack} key={rack.title}>
          <div className={styles.rackHead}>
            <h2>{rack.title}</h2>
            <div className={styles.rail} />
            <span className={styles.count}>{rack.code}</span>
          </div>
          <div className={styles.modules}>
            {rack.modules.map((mod) => {
              const state = moduleState(mod, status);
              const hay = `${mod.name} ${mod.desc} ${mod.keywords ?? ''}`;
              const lit = mod.project ? citedProjects.has(mod.project) : false;
              const hidden = !matchesQuery(hay, q);
              const primary = moduleHref(mod);
              const openPrimary = () => window.open(primary, '_blank', 'noopener,noreferrer');
              return (
                <div
                  key={mod.name}
                  className={`${styles.mod} ${styles[state]} ${lit ? styles.cited : ''} ${hidden ? styles.hide : ''}`}
                  role="link"
                  tabIndex={0}
                  onClick={openPrimary}
                  onKeyDown={(e) => { if (e.key === 'Enter') openPrimary(); }}
                >
                  <div className={styles.modTop}>
                    <span className={styles.led} />
                    <span className={styles.modName}>{mod.name}</span>
                    {mod.port && <span className={styles.modPort}>:{mod.port}</span>}
                  </div>
                  <div className={styles.modDesc}>{mod.desc}</div>
                  <div className={styles.jacks} onClick={(e) => e.stopPropagation()}>
                    {mod.jacks.map((jack) => {
                      const href = jack === 'TUNNEL'
                        ? mod.tunnel
                        : jack === 'LAN'
                          ? `${LAN}:${mod.port}${mod.path ?? ''}`
                          : `${TS}:${mod.port}${mod.path ?? ''}`;
                      return (
                        <a
                          key={jack}
                          className={`${styles.jack} ${jack === 'TUNNEL' ? styles.jackHot : ''}`}
                          href={href}
                          target="_blank"
                          rel="noopener noreferrer"
                        >{jack}</a>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ))}

      <section className={styles.rack}>
        <div className={styles.rackHead}>
          <h2>Documentation</h2>
          <div className={styles.rail} />
          <span className={styles.count}>SHELF A</span>
        </div>
        <div className={styles.shelf}>
          {tapes.map((tape: Tape) => {
            const hay = `${tape.title} ${tape.desc} ${tape.keywords ?? ''}`;
            const lit = citedProjects.has(tape.project);
            const hidden = !matchesQuery(hay, q);
            return (
              <Link
                key={tape.project}
                className={`${styles.tape} ${lit ? styles.cited : ''} ${hidden ? styles.hide : ''}`}
                to={tape.href}
              >
                <div className={styles.spine}><span>{tape.spine}</span></div>
                <div className={styles.tapeBody}>
                  <h3>{tape.title}</h3>
                  <p>{tape.desc}</p>
                  <span className={styles.go}>read the docs →</span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      <section className={styles.offsite}>
        <div className={styles.rackHead}>
          <h2>Offsite</h2>
          <div className={styles.rail} />
          <span className={styles.count}>EXT</span>
        </div>
        <ul>
          {offsite.map((link) => (
            <li key={link.href}>
              <a href={link.href} target="_blank" rel="noopener noreferrer">{link.label}</a>
            </li>
          ))}
        </ul>
      </section>

      <footer className={styles.foot}>
        <span>DIGITAL HARMONY GROUP — AI AGENTS IN TUNE WITH YOU</span>
        <span>g700data1 · 10.0.0.251 · TS 100.107.14.51</span>
      </footer>
    </div>
  );
}
