import { useEffect, useState } from "react";
import { labComplete, labsList, labsRecommend } from "../api";

type Lab = {
  id: string;
  title: string;
  effort_hours: number;
  weakness_tags: string[];
  steps: string[];
};

export function LabsPage() {
  const [labs, setLabs] = useState<Lab[]>([]);
  const [rec, setRec] = useState<Lab[]>([]);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    labsList().then((d) => setLabs(d.labs || []));
    labsRecommend().then((d) => setRec(d.labs || []));
  }, []);

  async function complete(labId: string) {
    await labComplete(labId, notes);
    setNotes("");
    alert("已记录完成");
  }

  return (
    <div className="split">
      <section>
        <div className="panel">
          <h3 className="panel-header">推荐练习</h3>
          {rec.length === 0 && <p className="empty-hint">完成刷题或模拟面试后将有个性推荐</p>}
          {rec.map((l) => (
            <article key={l.id} className="lab-card">
              <h4 className="lab-title">{l.title}</h4>
              <p className="lab-meta">约 {l.effort_hours} 小时</p>
              <div>
                {l.weakness_tags?.map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section>
        <div className="panel">
          <h3 className="panel-header">全部 Lab</h3>
          {labs.map((l) => (
            <article key={l.id} className="lab-card">
              <h4 className="lab-title">{l.title}</h4>
              <p className="lab-meta">约 {l.effort_hours} 小时</p>
              <ol className="lab-steps">
                {l.steps?.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
              <button type="button" className="btn" onClick={() => complete(l.id)}>
                完成打卡
              </button>
            </article>
          ))}
          <div className="field" style={{ marginTop: "1rem" }}>
            <label htmlFor="lab-notes">完成笔记</label>
            <textarea
              id="lab-notes"
              rows={2}
              placeholder="可选：记录收获或链接"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
