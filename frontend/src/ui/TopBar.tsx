/**
 * The top bar: whole-session actions that sit above the editor. Load the demo
 * coil or a blank one, or import/export a session file (`.jstc`). Import and
 * export round-trip the *whole* session — geometry plus the last computed
 * outputs and their cached matrix bundle — so a reloaded coil shows results
 * without recomputing. All loads go through the store's `loadSession`, so each
 * is a single undo step and sets the stale/up-to-date state correctly.
 */
import { useRef, useState } from 'react';

import { blankCoil, defaultCoil } from '../domain/coil';
import { useEditorStore } from '../state/store';
import {
  CoilFileError,
  exportFilename,
  parseSession,
  serializeSession,
} from '../state/coilFile';

type Notice = { kind: 'error' | 'info'; text: string } | null;

/** `dirty` (results stale vs. the coil) is derived by the analysis hook, so
 *  it is passed in — it becomes the exported session's `stale` flag. */
export function TopBar({ dirty }: { dirty: boolean }) {
  const loadSession = useEditorStore((s) => s.loadSession);
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  const loadDemo = () => {
    loadSession({ coil: defaultCoil(), analysis: null, stale: false });
    setNotice(null);
  };

  const loadNew = () => {
    loadSession({ coil: blankCoil(), analysis: null, stale: false });
    setNotice(null);
  };

  const exportSession = () => {
    const { coil, analysis, unitPrefs } = useEditorStore.getState();
    const text = serializeSession({ coil, analysis, stale: dirty, unitPrefs });
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = exportFilename();
    a.click();
    URL.revokeObjectURL(url);
  };

  const pickFile = () => fileInput.current?.click();

  const onFileChosen = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset the input so choosing the same file again re-triggers onChange.
    e.target.value = '';
    if (!file) return;
    try {
      const session = parseSession(await file.text());
      loadSession(session);
      setNotice(
        session.warnings.length
          ? { kind: 'info', text: session.warnings.join(' ') }
          : null,
      );
    } catch (err) {
      const text =
        err instanceof CoilFileError
          ? err.message
          : `Could not import "${file.name}".`;
      setNotice({ kind: 'error', text });
    }
  };

  return (
    <div className="topbar" data-testid="topbar">
      <div className="topbar-brand">
        <span className="topbar-brand-mark" aria-hidden="true" />
        JSTC
      </div>
      <div className="topbar-group">
        <button type="button" className="topbar-btn" data-testid="topbar-demo" onClick={loadDemo}>
          Demo coil
        </button>
        <button type="button" className="topbar-btn" data-testid="topbar-new" onClick={loadNew}>
          New coil
        </button>
        <button type="button" className="topbar-btn" data-testid="topbar-import" onClick={pickFile}>
          Import…
        </button>
        <button type="button" className="topbar-btn" data-testid="topbar-export" onClick={exportSession}>
          Export
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".jstc,.json,application/json"
          data-testid="topbar-file-input"
          style={{ display: 'none' }}
          onChange={onFileChosen}
        />
      </div>

      <a
        className="topbar-github"
        href="https://github.com/PartialScience/JSTC"
        target="_blank"
        rel="noreferrer noopener"
        data-testid="topbar-github"
        aria-label="View source on GitHub"
        title="View source on GitHub"
      >
        {/* Official GitHub mark; inherits color via currentColor. */}
        <svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor" aria-hidden="true">
          <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
        </svg>
      </a>

      {notice && (
        <div
          className={notice.kind === 'error' ? 'topbar-notice error' : 'topbar-notice'}
          data-testid="topbar-notice"
          role={notice.kind === 'error' ? 'alert' : 'status'}
        >
          <span>{notice.text}</span>
          <button
            type="button"
            className="topbar-notice-dismiss"
            aria-label="Dismiss"
            onClick={() => setNotice(null)}
          >
            ✕
          </button>
        </div>
      )}
    </div>
  );
}
