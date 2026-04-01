import { useMemo, useState } from 'react';
import { ChapterType } from '../pages/Home';
import createVideoClip from '../api/actions/createVideoClip';
import Button from './Button';
import iconClose from '/img/icon-close.svg';

type Props = {
  videoId: string;
  videoTitle: string;
  chapters?: ChapterType[];
  description?: string;
  onClose: () => void;
};

/** Parse "MM:SS" or "H:MM:SS" timecode string to total seconds */
function parseTimecodeStr(tc: string): number {
  const parts = tc.split(':').map(Number);
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return parts[0] * 3600 + parts[1] * 60 + parts[2];
}

/** Extract chapter list from description text timestamps, e.g. "03:50 - На что снимать?" */
function parseDescriptionChapters(description: string): ChapterType[] {
  const regex = /(?:^|\n)(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–]\s*(.+)/g;
  const matches = [...description.matchAll(regex)];
  if (matches.length < 2) return [];
  return matches.map((m, i) => ({
    start_time: parseTimecodeStr(m[1]),
    // last chapter: use next chapter start, or a large sentinel so ffmpeg reads to end
    end_time: i + 1 < matches.length ? parseTimecodeStr(matches[i + 1][1]) : 99999,
    title: m[2].trim(),
  }));
}

/** Format seconds as MM:SS */
const formatSeconds = (sec: number): string => {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};

/** Build segment string from a list of selected chapter pairs */
const chaptersToSegments = (selected: ChapterType[]): string => {
  return selected.map(c => `${formatSeconds(c.start_time)}-${formatSeconds(c.end_time)}`).join(',');
};

const VideoCutDialog = ({ videoId, videoTitle, chapters, description, onClose }: Props) => {
  const effectiveChapters = useMemo<ChapterType[]>(() => {
    if (chapters && chapters.length > 0) return chapters;
    if (description) return parseDescriptionChapters(description);
    return [];
  }, [chapters, description]);

  const [segments, setSegments] = useState('');
  const [clipTitle, setClipTitle] = useState('');
  const [selectedChapters, setSelectedChapters] = useState<Set<number>>(new Set());
  const [status, setStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const toggleChapter = (idx: number) => {
    setSelectedChapters(prev => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  const applySelectedChapters = () => {
    const selected = effectiveChapters.filter((_, i) => selectedChapters.has(i));
    if (selected.length === 0) return;
    setSegments(chaptersToSegments(selected));
  };

  const selectAllChapters = () => {
    setSelectedChapters(new Set(effectiveChapters.map((_, i) => i)));
    setSegments(chaptersToSegments(effectiveChapters));
  };

  const handleSubmit = async () => {
    if (!segments.trim()) return;
    setStatus('submitting');
    setErrorMsg('');
    try {
      const resp = await createVideoClip(videoId, {
        segments: segments.trim(),
        title: clipTitle.trim() || undefined,
      });
      if (resp.error) {
        const raw = resp.error?.error ?? resp.error;
        setErrorMsg(typeof raw === 'string' ? raw : JSON.stringify(raw));
        setStatus('error');
      } else {
        setStatus('done');
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setErrorMsg(msg);
      setStatus('error');
    }
  };

  return (
    <div className="video-popup-menu">
      <img
        src={iconClose}
        className="video-popup-menu-close-button"
        title="Close"
        onClick={onClose}
      />
      <h3>Cut Clip from &ldquo;{videoTitle}&rdquo;</h3>

      {status === 'done' ? (
        <>
          <p>Clip task started. The clip will appear in your archive shortly.</p>
          <Button label="Close" onClick={onClose} />
        </>
      ) : (
        <>
          {effectiveChapters.length > 0 && (
            <div className="cut-chapters">
              <p>
                <strong>Chapters</strong>{' '}
                <button type="button" onClick={selectAllChapters} style={{ marginLeft: 8 }}>
                  Select all
                </button>
              </p>
              <ul style={{ listStyle: 'none', padding: 0, maxHeight: 200, overflowY: 'auto' }}>
                {effectiveChapters.map((ch, i) => (
                  <li key={i}>
                    <label style={{ cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={selectedChapters.has(i)}
                        onChange={() => toggleChapter(i)}
                        style={{ marginRight: 6 }}
                      />
                      {formatSeconds(ch.start_time)}–{ch.end_time >= 99999 ? 'end' : formatSeconds(ch.end_time)} {ch.title}
                    </label>
                  </li>
                ))}
              </ul>
              <Button
                label="Use selected chapters"
                onClick={applySelectedChapters}
              />
            </div>
          )}

          <p style={{ marginTop: 12 }}>
            <strong>Timecodes</strong> (e.g. <code>00:15-01:25,16:21-18:10</code>)
          </p>
          <input
            type="text"
            value={segments}
            onChange={e => setSegments(e.target.value)}
            placeholder="MM:SS-MM:SS,MM:SS-MM:SS"
            style={{ width: '100%', marginBottom: 8 }}
          />

          <p>
            <strong>Clip title</strong> (optional)
          </p>
          <input
            type="text"
            value={clipTitle}
            onChange={e => setClipTitle(e.target.value)}
            placeholder={`${videoTitle} [clip]`}
            style={{ width: '100%', marginBottom: 8 }}
          />

          {status === 'error' && (
            <p style={{ color: 'red' }}>Error: {errorMsg}</p>
          )}

          <Button
            label={status === 'submitting' ? 'Starting…' : 'Create Clip'}
            disabled={status === 'submitting' || !segments.trim()}
            onClick={handleSubmit}
          />
        </>
      )}
    </div>
  );
};

export default VideoCutDialog;
