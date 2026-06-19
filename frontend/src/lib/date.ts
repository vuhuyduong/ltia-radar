/**
 * Utility functions for formatting relative dates in Vietnamese.
 */

export interface TableDateResult {
  line1: string;
  line2: string;
}

export function ensureUtcString(dateStr: string): string {
  if (!dateStr.endsWith("Z") && !/[+-]\d{2}:\d{2}$/.test(dateStr)) {
    return dateStr + "Z";
  }
  return dateStr;
}

export function getVietnamParts(date: Date) {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
    hour12: false,
    hourCycle: "h23",
  });
  
  const parts = formatter.formatToParts(date);
  const partMap: Record<string, string> = {};
  for (const part of parts) {
    partMap[part.type] = part.value;
  }
  
  return {
    year: parseInt(partMap.year, 10),
    month: parseInt(partMap.month, 10),
    day: parseInt(partMap.day, 10),
    hours: parseInt(partMap.hour, 10),
    minutes: parseInt(partMap.minute, 10),
    seconds: parseInt(partMap.second, 10),
  };
}

export function formatTableDate(dateInput: string | Date | null | undefined): TableDateResult {
  if (!dateInput) return { line1: "Chưa rõ", line2: "" };
  const date = typeof dateInput === "string" ? new Date(ensureUtcString(dateInput)) : dateInput;
  if (isNaN(date.getTime())) return { line1: "Chưa rõ", line2: "" };

  const vnParts = getVietnamParts(date);
  const todayVNParts = getVietnamParts(new Date());

  const todayVN = new Date(todayVNParts.year, todayVNParts.month - 1, todayVNParts.day, 0, 0, 0, 0);
  const targetVN = new Date(vnParts.year, vnParts.month - 1, vnParts.day, 0, 0, 0, 0);

  const diffTime = todayVN.getTime() - targetVN.getTime();
  const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));

  const dateStr = `${vnParts.day}/${vnParts.month}/${vnParts.year}`;

  if (diffDays === 0) {
    return { line1: "Hôm nay", line2: `(${dateStr})` };
  } else if (diffDays === 1) {
    return { line1: "Hôm qua", line2: `(${dateStr})` };
  } else if (diffDays > 1) {
    return { line1: dateStr, line2: `(${diffDays} ngày trước)` };
  } else {
    // For future dates or fallback
    return { line1: dateStr, line2: "" };
  }
}

export function formatArticleDate(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return "Chưa rõ";
  const date = typeof dateInput === "string" ? new Date(ensureUtcString(dateInput)) : dateInput;
  if (isNaN(date.getTime())) return "Chưa rõ";

  const vnParts = getVietnamParts(date);
  const todayVNParts = getVietnamParts(new Date());

  const todayVN = new Date(todayVNParts.year, todayVNParts.month - 1, todayVNParts.day, 0, 0, 0, 0);
  const targetVN = new Date(vnParts.year, vnParts.month - 1, vnParts.day, 0, 0, 0, 0);

  const diffTime = todayVN.getTime() - targetVN.getTime();
  const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));

  const hours = String(vnParts.hours).padStart(2, "0");
  const minutes = String(vnParts.minutes).padStart(2, "0");
  const seconds = String(vnParts.seconds).padStart(2, "0");
  const timeStr = `${hours}:${minutes}:${seconds}`;

  const dateStrNoPad = `${vnParts.day}/${vnParts.month}/${vnParts.year}`;

  if (diffDays === 0) {
    return `${timeStr}, Hôm nay (${dateStrNoPad})`;
  } else if (diffDays === 1) {
    return `${timeStr}, Hôm qua (${dateStrNoPad})`;
  } else if (diffDays > 1) {
    return `${timeStr}, ${dateStrNoPad} (${diffDays} ngày trước)`;
  } else {
    // For future dates or fallback
    return `${timeStr}, ${dateStrNoPad}`;
  }
}

