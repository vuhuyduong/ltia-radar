/**
 * Danh mục Gói thầu và Cụm gói thầu Dự án Cảng HKQT Long Thành
 * Căn cứ Báo cáo số 424/BC-BXD của Bộ Xây dựng và Thực tiễn triển khai (Tháng 11/2026).
 */

export interface PackageOption {
  value: string;
  label: string;
  badgeClass?: string;
  isCritical?: boolean;
}

export interface PackageGroup {
  groupName: string;
  options: PackageOption[];
}

export const BXD_PACKAGE_GROUPS: PackageGroup[] = [
  {
    groupName: "Cụm 04 Gói thầu Đường găng BXD (Đặc biệt quan trọng)",
    options: [
      {
        value: "Gói thầu 5.10",
        label: "Gói 5.10 — Nhà ga hành khách (35.000 tỷ, VIETUR)",
        isCritical: true,
      },
      {
        value: "Gói thầu 4.8",
        label: "Gói 4.8 — Giao thông nội cảng & Hạ tầng kỹ thuật (11.440 tỷ)",
        isCritical: true,
      },
      {
        value: "Gói thầu 7.8",
        label: "Gói 7.8 — Nhà ga hàng hóa số 1 (3.400 tỷ, HANTA2)",
        isCritical: true,
      },
      {
        value: "Gói thầu 11.5",
        label: "Gói 11.5 — Nhà để xe & Công trình phụ trợ (3.144 tỷ)",
        isCritical: true,
      },
    ],
  },
  {
    groupName: "Khu bay & Đường cất hạ cánh (CHC)",
    options: [
      {
        value: "Gói thầu 4.6",
        label: "Gói 4.6 — Đường cất hạ cánh số 1 & Sân đỗ khu bay",
      },
      {
        value: "Gói thầu 4.12",
        label: "Gói 4.12 — Đường cất hạ cánh số 2 (3.300 tỷ)",
      },
      {
        value: "Gói thầu 4.7",
        label: "Gói 4.7 — Sân đỗ tàu bay Nhà ga HK & Hầm GSE",
      },
      {
        value: "Đường cất hạ cánh",
        label: "Hạng mục Đường cất hạ cánh (Chung)",
      },
    ],
  },
  {
    groupName: "Hạ tầng phụ trợ, Thiết bị & Môi trường",
    options: [
      {
        value: "Gói thầu 4.9",
        label: "Gói 4.9 — Hệ thống tra nạp nhiên liệu tàu bay (LAFS)",
      },
      {
        value: "Gói thầu 5.11",
        label: "Gói 5.11 — Thiết bị CNTT & Viễn thông ICT toàn cảng",
      },
      {
        value: "Gói thầu 4.11",
        label: "Gói 4.11 — Trạm xử lý nước thải",
      },
      {
        value: "Gói thầu 3.4",
        label: "Gói 3.4 — San nền & Thoát nước (Khu bay)",
      },
      {
        value: "San nền",
        label: "Hạng mục San nền (Chung)",
      },
    ],
  },
  {
    groupName: "Các Dự án thành phần khác (DATP 1, 2, 4)",
    options: [
      {
        value: "DATP 1",
        label: "DATP 1 — Trụ sở Cơ quan Quản lý Nhà nước",
      },
      {
        value: "Gói thầu XD02",
        label: "Gói XD02 / DATP 2 — Tháp kiểm soát không lưu 123m (VATM)",
      },
      {
        value: "DATP 4",
        label: "DATP 4 — Công trình Dịch vụ HK (Express Cargo, Hangar, Khách sạn)",
      },
    ],
  },
  {
    groupName: "Giao thông kết nối & Hạ tầng ngoại cảng",
    options: [
      {
        value: "Gói thầu 6.12",
        label: "Gói 6.12 — Tuyến giao thông kết nối T1 & T2 (Đèo Cả)",
      },
      {
        value: "Cao tốc TP.HCM - Long Thành",
        label: "Cao tốc TP.HCM — Long Thành & Nút giao An Phú",
      },
      {
        value: "Nút giao An Phú",
        label: "Nút giao An Phú (Cửa ngõ TP.HCM)",
      },
      {
        value: "Cao tốc Biên Hòa - Vũng Tàu",
        label: "Cao tốc Biên Hòa — Vũng Tàu",
      },
      {
        value: "Cao tốc Bến Lức - Long Thành",
        label: "Cao tốc Bến Lức — Long Thành",
      },
      {
        value: "Đường sắt Thủ Thiêm - Long Thành",
        label: "Đường sắt nhẹ Thủ Thiêm — Long Thành",
      },
      {
        value: "Giao thông",
        label: "Hạng mục Giao thông kết nối (Chung)",
      },
    ],
  },
  {
    groupName: "Phạm vi vận hành & Toàn dự án",
    options: [
      {
        value: "Toàn dự án",
        label: "Toàn dự án Sân bay Long Thành",
      },
      {
        value: "Nhà ga",
        label: "Hạng mục Nhà ga (Chung)",
      },
      {
        value: "ORAT & Khai thác",
        label: "Thử nghiệm ORAT & Chuyển đổi khai thác TSN ↔ LTIA",
      },
    ],
  },
];

/**
 * Kiểm tra xem một nhãn scope có phải thuộc cụm gói đường găng BXD không
 */
export function isBxdCriticalScope(scope: string): boolean {
  return ["Gói thầu 5.10", "Gói thầu 4.8", "Gói thầu 7.8", "Gói thầu 11.5"].includes(scope);
}
