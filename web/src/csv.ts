// Minimal RFC 4180 reader used only to list the distinct values of the chosen target column
// (the dataset profile has counts, not values). The server stays the source of truth.
export async function readText(file: File): Promise<string> {
  return await file.text();
}

export function distinctValues(text: string, header: string, cap = 60): { values: string[]; capped: boolean } {
  const out = new Set<string>();
  let col = -1;
  let row = 0;
  let field = "";
  let inQ = false;
  let idx = 0;
  let capped = false;
  const endField = () => {
    if (row === 0) {
      if (field.replace(/^﻿/, "").trim() === header) col = idx;
    } else if (idx === col) {
      const v = field.trim();
      if (v !== "") out.add(v);
      if (out.size > cap) capped = true;
    }
    field = "";
    idx++;
  };
  for (let i = 0; i < text.length && !capped; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false;
      } else field += c;
    } else if (c === '"') inQ = true;
    else if (c === ",") endField();
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      endField();
      row++;
      idx = 0;
      if (row === 1 && col < 0) break;
    } else field += c;
  }
  if (field !== "" || idx > 0) endField();
  return { values: Array.from(out).sort(), capped };
}
