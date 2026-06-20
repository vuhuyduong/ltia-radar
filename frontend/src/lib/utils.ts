import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const getFriendlyDomain = (url: string | undefined): string => {
  if (!url) return "Nguồn";
  try {
    const domain = new URL(url).hostname;
    if (domain.includes("vnexpress.net")) return "VnExpress";
    if (domain.includes("tuoitre.vn")) return "Tuổi Trẻ";
    if (domain.includes("thanhnien.vn")) return "Thanh Niên";
    if (domain.includes("dantri.com.vn")) return "Dân Trí";
    if (domain.includes("vietnamnet.vn")) return "Vietnamnet";
    if (domain.includes("vtv.vn")) return "VTV News";
    if (domain.includes("laodong.vn")) return "Lao Động";
    if (domain.includes("tienphong.vn")) return "Tiền Phong";
    if (domain.includes("nld.com.vn")) return "Người Lao Động";
    if (domain.includes("baogiaothong.vn")) return "Báo Giao Thông";
    if (domain.includes("baoxaydung.com.vn")) return "Báo Xây Dựng";
    if (domain.includes("nhandan.vn")) return "Nhân Dân";
    if (domain.includes("chinhphu.vn") || domain.includes("baochinhphu.vn")) return "Báo Chính Phủ";
    if (domain.includes("vneconomy.vn")) return "VnEconomy";
    if (domain.includes("cafef.vn")) return "CafeF";
    if (domain.includes("thanhuytphcm.vn")) return "Thành ủy TPHCM";
    if (domain.includes("dongnai.gov.vn")) return "Cổng TTĐT Đồng Nai";
    
    // Fallback: capitalize first letter of domain parts
    let cleanDomain = domain;
    if (cleanDomain.startsWith("www.")) {
      cleanDomain = cleanDomain.substring(4);
    }
    const parts = cleanDomain.split(".");
    if (parts.length > 0) {
      const name = parts[0];
      return name.charAt(0).toUpperCase() + name.slice(1);
    }
    return cleanDomain;
  } catch (error) {
    return "Nguồn";
  }
};

export const getEarliestPublishDate = (item: any): Date | string | null => {
  // If there are citations, find the earliest publish_time
  if (item.citations && Array.isArray(item.citations) && item.citations.length > 0) {
    let earliest: Date | null = null;
    for (const citation of item.citations) {
      if (citation.publish_time) {
        const d = new Date(citation.publish_time);
        if (!isNaN(d.getTime())) {
          if (!earliest || d < earliest) {
            earliest = d;
          }
        }
      }
    }
    if (earliest) return earliest;
  }
  // Fallback to publish_time, or processed_time
  return item.publish_time || item.processed_time || null;
};
