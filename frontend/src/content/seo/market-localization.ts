import { defaultLocale } from '@/i18n/config';
import type {
  SeoCallToAction,
  SeoHubCard,
  SeoHubContent,
  SeoResourceLink,
  SeoStaticKnowledgePage,
} from '@/content/seo/types';

export const seoPriorityMarketLocales = [
  'en-EN',
  'ru-RU',
  'zh-CN',
  'hi-IN',
  'id-ID',
  'vi-VN',
  'th-TH',
  'ja-JP',
  'ko-KR',
] as const;

export type SeoPriorityMarketLocale = (typeof seoPriorityMarketLocales)[number];

type SeoUiLabels = {
  home: string;
  guides: string;
  compare: string;
  devices: string;
  trustCenter: string;
  audits: string;
  backToHomepage: string;
  backToGuides: string;
  backToCompare: string;
  backToDevices: string;
  hubIntent: string;
  readPage: string;
  nextAction: string;
  relatedRoutes: string;
  updated: string;
};

type LocalizedHubCopy = {
  badge: string;
  title: string;
  description: string;
  bullets: readonly string[];
  proofPoints: readonly string[];
  cards: readonly Pick<SeoHubCard, 'eyebrow' | 'title' | 'description'>[];
  ctaLinks: readonly Pick<SeoCallToAction, 'label' | 'description'>[];
};

type LocalizedKnowledgeCopy = {
  badge: string;
  title: string;
  description: string;
  heroPoints: readonly string[];
  sections: SeoStaticKnowledgePage['sections'];
  relatedLinks: readonly SeoResourceLink[];
  ctaLinks: readonly SeoCallToAction[];
};

const SEO_UI_LABELS: Record<SeoPriorityMarketLocale, SeoUiLabels> = {
  'en-EN': {
    home: 'Home',
    guides: 'Guides',
    compare: 'Compare',
    devices: 'Devices',
    trustCenter: 'Trust center',
    audits: 'Audits',
    backToHomepage: 'Back to homepage',
    backToGuides: 'Back to guides',
    backToCompare: 'Back to compare',
    backToDevices: 'Back to devices',
    hubIntent: 'Hub intent',
    readPage: 'Read page',
    nextAction: 'Next action',
    relatedRoutes: 'Related routes',
    updated: 'Updated',
  },
  'ru-RU': {
    home: 'Главная',
    guides: 'Гайды',
    compare: 'Сравнения',
    devices: 'Устройства',
    trustCenter: 'Центр доверия',
    audits: 'Аудиты',
    backToHomepage: 'Назад на главную',
    backToGuides: 'Назад к гайдам',
    backToCompare: 'Назад к сравнениям',
    backToDevices: 'Назад к устройствам',
    hubIntent: 'Смысл хаба',
    readPage: 'Открыть страницу',
    nextAction: 'Следующий шаг',
    relatedRoutes: 'Связанные маршруты',
    updated: 'Обновлено',
  },
  'zh-CN': {
    home: '首页',
    guides: '指南',
    compare: '对比',
    devices: '设备',
    trustCenter: '信任中心',
    audits: '审计',
    backToHomepage: '返回首页',
    backToGuides: '返回指南',
    backToCompare: '返回对比',
    backToDevices: '返回设备',
    hubIntent: '页面意图',
    readPage: '打开页面',
    nextAction: '下一步',
    relatedRoutes: '相关页面',
    updated: '更新于',
  },
  'hi-IN': {
    home: 'होम',
    guides: 'गाइड्स',
    compare: 'तुलना',
    devices: 'डिवाइस',
    trustCenter: 'ट्रस्ट सेंटर',
    audits: 'ऑडिट',
    backToHomepage: 'होम पर वापस जाएँ',
    backToGuides: 'गाइड्स पर वापस जाएँ',
    backToCompare: 'तुलना पर वापस जाएँ',
    backToDevices: 'डिवाइस पेज पर वापस जाएँ',
    hubIntent: 'हब का उद्देश्य',
    readPage: 'पेज खोलें',
    nextAction: 'अगला कदम',
    relatedRoutes: 'संबंधित रूट्स',
    updated: 'अपडेट',
  },
  'id-ID': {
    home: 'Beranda',
    guides: 'Panduan',
    compare: 'Perbandingan',
    devices: 'Perangkat',
    trustCenter: 'Pusat kepercayaan',
    audits: 'Audit',
    backToHomepage: 'Kembali ke beranda',
    backToGuides: 'Kembali ke panduan',
    backToCompare: 'Kembali ke perbandingan',
    backToDevices: 'Kembali ke perangkat',
    hubIntent: 'Maksud hub',
    readPage: 'Buka halaman',
    nextAction: 'Langkah berikutnya',
    relatedRoutes: 'Rute terkait',
    updated: 'Diperbarui',
  },
  'vi-VN': {
    home: 'Trang chủ',
    guides: 'Hướng dẫn',
    compare: 'So sánh',
    devices: 'Thiết bị',
    trustCenter: 'Trung tâm tin cậy',
    audits: 'Kiểm toán',
    backToHomepage: 'Quay lại trang chủ',
    backToGuides: 'Quay lại hướng dẫn',
    backToCompare: 'Quay lại phần so sánh',
    backToDevices: 'Quay lại thiết bị',
    hubIntent: 'Ý định của hub',
    readPage: 'Mở trang',
    nextAction: 'Bước tiếp theo',
    relatedRoutes: 'Trang liên quan',
    updated: 'Cập nhật',
  },
  'th-TH': {
    home: 'หน้าแรก',
    guides: 'คู่มือ',
    compare: 'เปรียบเทียบ',
    devices: 'อุปกรณ์',
    trustCenter: 'ศูนย์ความน่าเชื่อถือ',
    audits: 'การตรวจสอบ',
    backToHomepage: 'กลับหน้าแรก',
    backToGuides: 'กลับไปที่คู่มือ',
    backToCompare: 'กลับไปที่การเปรียบเทียบ',
    backToDevices: 'กลับไปที่อุปกรณ์',
    hubIntent: 'เป้าหมายของฮับ',
    readPage: 'เปิดหน้า',
    nextAction: 'ขั้นตอนถัดไป',
    relatedRoutes: 'หน้าที่เกี่ยวข้อง',
    updated: 'อัปเดต',
  },
  'ja-JP': {
    home: 'ホーム',
    guides: 'ガイド',
    compare: '比較',
    devices: 'デバイス',
    trustCenter: 'トラストセンター',
    audits: '監査',
    backToHomepage: 'ホームに戻る',
    backToGuides: 'ガイドに戻る',
    backToCompare: '比較一覧に戻る',
    backToDevices: 'デバイス一覧に戻る',
    hubIntent: 'ハブの意図',
    readPage: 'ページを開く',
    nextAction: '次のアクション',
    relatedRoutes: '関連ルート',
    updated: '更新',
  },
  'ko-KR': {
    home: '홈',
    guides: '가이드',
    compare: '비교',
    devices: '기기',
    trustCenter: '트러스트 센터',
    audits: '감사',
    backToHomepage: '홈으로 돌아가기',
    backToGuides: '가이드로 돌아가기',
    backToCompare: '비교로 돌아가기',
    backToDevices: '기기로 돌아가기',
    hubIntent: '허브 목적',
    readPage: '페이지 열기',
    nextAction: '다음 단계',
    relatedRoutes: '관련 경로',
    updated: '업데이트',
  },
};

function extractLeadingNumber(value: string): number | undefined {
  const matchedNumber = value.match(/\d+/)?.[0];

  return matchedNumber ? Number.parseInt(matchedNumber, 10) : undefined;
}

function formatRussianSectionCount(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;

  if (mod10 === 1 && mod100 !== 11) {
    return `${count} раздел`;
  }

  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} раздела`;
  }

  return `${count} разделов`;
}

export function resolveSeoPriorityMarketLocale(locale?: string): SeoPriorityMarketLocale {
  if (locale && seoPriorityMarketLocales.includes(locale as SeoPriorityMarketLocale)) {
    return locale as SeoPriorityMarketLocale;
  }

  return defaultLocale;
}

export function getSeoUiLabels(locale?: string): SeoUiLabels {
  return SEO_UI_LABELS[resolveSeoPriorityMarketLocale(locale)];
}

export function localizeSeoReadingTime(readingTime: string, locale?: string): string {
  const minutes = extractLeadingNumber(readingTime);
  const resolvedLocale = resolveSeoPriorityMarketLocale(locale);

  if (!minutes) {
    return readingTime;
  }

  switch (resolvedLocale) {
    case 'ru-RU':
      return `${minutes} мин чтения`;
    case 'zh-CN':
      return `阅读约 ${minutes} 分钟`;
    case 'hi-IN':
      return `${minutes} मिनट पढ़ें`;
    case 'id-ID':
      return `${minutes} mnt baca`;
    case 'vi-VN':
      return `${minutes} phút đọc`;
    case 'th-TH':
      return `อ่าน ${minutes} นาที`;
    case 'ja-JP':
      return `${minutes}分で読めます`;
    case 'ko-KR':
      return `${minutes}분 읽기`;
    default:
      return `${minutes} min read`;
  }
}

export function formatSeoUpdatedAt(updatedAt: string, locale?: string): string {
  return `${getSeoUiLabels(locale).updated} ${updatedAt}`;
}

export function formatSeoSectionCount(count: number, locale?: string): string {
  const resolvedLocale = resolveSeoPriorityMarketLocale(locale);

  switch (resolvedLocale) {
    case 'ru-RU':
      return formatRussianSectionCount(count);
    case 'zh-CN':
      return `${count} 个部分`;
    case 'hi-IN':
      return `${count} सेक्शन`;
    case 'id-ID':
      return `${count} bagian`;
    case 'vi-VN':
      return `${count} phần`;
    case 'th-TH':
      return `${count} ส่วน`;
    case 'ja-JP':
      return `${count} セクション`;
    case 'ko-KR':
      return `${count}개 섹션`;
    default:
      return `${count} sections`;
  }
}

export function localizeHubContent(
  base: SeoHubContent,
  localizedContent: Partial<Record<SeoPriorityMarketLocale, LocalizedHubCopy>>,
  locale?: string,
): SeoHubContent {
  const resolvedLocale = resolveSeoPriorityMarketLocale(locale);
  const localized = localizedContent[resolvedLocale] ?? localizedContent['en-EN'];

  if (!localized) {
    return base;
  }

  return {
    ...base,
    badge: localized.badge,
    title: localized.title,
    description: localized.description,
    bullets: localized.bullets,
    proofPoints: localized.proofPoints,
    cards: base.cards.map((card, index) => ({
      ...card,
      eyebrow: localized.cards[index]?.eyebrow ?? card.eyebrow,
      title: localized.cards[index]?.title ?? card.title,
      description: localized.cards[index]?.description ?? card.description,
    })),
    ctaLinks: base.ctaLinks.map((link, index) => ({
      ...link,
      label: localized.ctaLinks[index]?.label ?? link.label,
      description: localized.ctaLinks[index]?.description ?? link.description,
    })),
  };
}

export function localizeKnowledgePage(
  base: SeoStaticKnowledgePage,
  localizedContent: Partial<Record<SeoPriorityMarketLocale, LocalizedKnowledgeCopy>>,
  locale?: string,
): SeoStaticKnowledgePage {
  const resolvedLocale = resolveSeoPriorityMarketLocale(locale);
  const localized = localizedContent[resolvedLocale] ?? localizedContent['en-EN'];

  if (!localized) {
    return base;
  }

  return {
    ...base,
    readingTime: localizeSeoReadingTime(base.readingTime, locale),
    badge: localized.badge,
    title: localized.title,
    description: localized.description,
    heroPoints: localized.heroPoints,
    sections: localized.sections,
    relatedLinks: localized.relatedLinks,
    ctaLinks: localized.ctaLinks,
  };
}

export const GUIDES_HUB_LOCALIZATION: Partial<Record<SeoPriorityMarketLocale, LocalizedHubCopy>> = {
  'en-EN': {
    badge: 'Operational playbooks',
    title: 'VPN guides that answer setup, speed, censorship, and trust questions with usable detail',
    description:
      'Server-rendered knowledge assets for users comparing VPN architectures, fixing hostile-network issues, and evaluating whether CyberVPN can be trusted in production.',
    bullets: [
      'Written to answer real search intent instead of vanity keyword lists.',
      'Focused on setup, performance, censorship resistance, and trust operations.',
      'Internally linked to pricing, devices, docs, trust, and audit evidence.',
    ],
    proofPoints: ['3 launch-ready guides', 'SSR HTML', 'Actionable internal CTAs'],
    cards: [
      {
        eyebrow: 'Censorship resistance',
        title: 'How to bypass DPI with VLESS Reality without wrecking latency',
        description:
          'Deploy a Reality-backed profile that survives hostile ISPs and stays practical for daily browsing and streaming.',
      },
      {
        eyebrow: 'Performance operations',
        title: 'VPN speed optimization for streaming and gaming sessions',
        description:
          'Trim avoidable latency by matching protocol choice and egress geography to the traffic you actually care about.',
      },
      {
        eyebrow: 'Trust operations',
        title: 'Zero-log VPN rollout checklist for distributed teams',
        description:
          'Ship a VPN stack to teams without creating shadow IT, weak onboarding, or vague logging assumptions.',
      },
    ],
    ctaLinks: [
      { label: 'Compare plans', description: 'Choose a plan with enough throughput and device slots.' },
      { label: 'Download clients', description: 'Get clients for Android, iOS, desktop, and sing-box based stacks.' },
      { label: 'Open trust center', description: 'Review logging stance, infrastructure controls, and abuse handling.' },
    ],
  },
  'ru-RU': {
    badge: 'Практические сценарии',
    title: 'VPN-гайды по настройке, скорости, обходу блокировок и доверию',
    description:
      'Серверные knowledge-страницы для пользователей, которые сравнивают VPN-архитектуры, решают проблемы в агрессивных сетях и проверяют, можно ли доверять CyberVPN в рабочем использовании.',
    bullets: [
      'Контент собран под реальный поисковый интент, а не под пустые ключевые слова.',
      'Фокус на настройке, производительности, обходе блокировок и trust-операциях.',
      'Все страницы связаны с тарифами, устройствами, документацией, trust center и аудитами.',
    ],
    proofPoints: ['3 стартовых гайда', 'SSR HTML', 'Чёткие CTA'],
    cards: [
      {
        eyebrow: 'Обход блокировок',
        title: 'Как обходить DPI с VLESS Reality без лишней задержки',
        description:
          'Настройка Reality-профиля, который переживает агрессивных провайдеров и остаётся пригодным для ежедневного трафика.',
      },
      {
        eyebrow: 'Оптимизация скорости',
        title: 'Как ускорить VPN для стриминга и игр',
        description:
          'Снижение лишней задержки за счёт правильного выбора протокола, региона и маршрута под конкретную нагрузку.',
      },
      {
        eyebrow: 'Запуск и доверие',
        title: 'Чек-лист запуска zero-log VPN для распределённых команд',
        description:
          'Как развернуть VPN для команды без теневого ИТ, слабого онбординга и размытых логging-практик.',
      },
    ],
    ctaLinks: [
      { label: 'Сравнить тарифы', description: 'Подберите тариф с нужной пропускной способностью и количеством устройств.' },
      { label: 'Скачать клиенты', description: 'Получите клиенты для Android, iOS, desktop и стеков на базе sing-box.' },
      { label: 'Открыть trust center', description: 'Посмотрите политику логирования, инфраструктурный контроль и обработку abuse-кейсов.' },
    ],
  },
  'zh-CN': {
    badge: '运营手册',
    title: '面向配置、速度、抗封锁与信任评估的 VPN 指南',
    description:
      '这些服务端渲染的知识页面面向正在比较 VPN 架构、处理高压网络环境并评估 CyberVPN 是否适合生产使用的用户。',
    bullets: [
      '内容围绕真实搜索意图，而不是空洞关键词。',
      '重点覆盖配置、性能、抗审查与信任运营。',
      '所有页面都连接到价格、设备、文档、信任中心和审计证据。',
    ],
    proofPoints: ['3 个首发指南', 'SSR HTML', '明确 CTA'],
    cards: [
      {
        eyebrow: '抗封锁',
        title: '如何用 VLESS Reality 绕过 DPI 且不过度增加延迟',
        description: '部署能够穿过高压 ISP 的 Reality 配置，并保持日常浏览与流媒体场景的可用性。',
      },
      {
        eyebrow: '性能优化',
        title: '面向流媒体和游戏的 VPN 速度优化',
        description: '通过协议、出口地区和路由选择减少可避免的延迟与抖动。',
      },
      {
        eyebrow: '信任运营',
        title: '面向分布式团队的 zero-log VPN 上线清单',
        description: '在避免影子 IT、薄弱入职流程和模糊日志假设的前提下部署团队 VPN。',
      },
    ],
    ctaLinks: [
      { label: '查看套餐', description: '选择带宽和设备数量合适的套餐。' },
      { label: '下载客户端', description: '获取 Android、iOS、桌面端以及 sing-box 相关客户端。' },
      { label: '打开信任中心', description: '查看日志立场、基础设施控制与 abuse 处理方式。' },
    ],
  },
  'hi-IN': {
    badge: 'ऑपरेशनल प्लेबुक',
    title: 'सेटअप, स्पीड, सेंसरशिप बायपास और ट्रस्ट पर केंद्रित VPN गाइड्स',
    description:
      'ये server-rendered knowledge pages उन उपयोगकर्ताओं के लिए हैं जो VPN आर्किटेक्चर की तुलना कर रहे हैं, hostile networks में समस्याएँ हल कर रहे हैं और CyberVPN पर भरोसा किया जा सकता है या नहीं यह जाँच रहे हैं.',
    bullets: [
      'सामग्री वास्तविक search intent पर आधारित है, न कि खाली keyword stuffing पर.',
      'फोकस सेटअप, performance, censorship resistance और trust operations पर है.',
      'हर पेज pricing, devices, docs, trust center और audits से जुड़ा है.',
    ],
    proofPoints: ['3 लॉन्च-ready गाइड्स', 'SSR HTML', 'स्पष्ट CTA'],
    cards: [
      { eyebrow: 'सेंसरशिप रेजिस्टेंस', title: 'VLESS Reality के साथ DPI को कम latency में कैसे बायपास करें', description: 'ऐसा Reality profile deploy करें जो restrictive ISP में भी काम करे.' },
      { eyebrow: 'परफॉर्मेंस ऑप्स', title: 'स्ट्रीमिंग और गेमिंग के लिए VPN speed optimization', description: 'Protocol और region selection से avoidable latency कम करें.' },
      { eyebrow: 'ट्रस्ट ऑप्स', title: 'डिस्ट्रिब्यूटेड टीमों के लिए zero-log VPN rollout checklist', description: 'टीम rollout को shadow IT और weak onboarding से बचाएँ.' },
    ],
    ctaLinks: [
      { label: 'प्लान तुलना देखें', description: 'ऐसा प्लान चुनें जिसमें पर्याप्त throughput और device slots हों.' },
      { label: 'क्लाइंट डाउनलोड करें', description: 'Android, iOS, desktop और sing-box आधारित clients प्राप्त करें.' },
      { label: 'ट्रस्ट सेंटर खोलें', description: 'Logging stance, infrastructure controls और abuse handling देखें.' },
    ],
  },
  'id-ID': {
    badge: 'Playbook operasional',
    title: 'Panduan VPN untuk setup, kecepatan, bypass sensor, dan evaluasi kepercayaan',
    description:
      'Halaman pengetahuan berbasis SSR ini ditujukan untuk pengguna yang membandingkan arsitektur VPN, mengatasi jaringan agresif, dan menilai apakah CyberVPN layak dipercaya untuk penggunaan nyata.',
    bullets: [
      'Ditulis untuk intent pencarian nyata, bukan sekadar daftar kata kunci.',
      'Berfokus pada setup, performa, resistensi sensor, dan operasi trust.',
      'Semua halaman terhubung ke pricing, device, docs, trust center, dan audit.',
    ],
    proofPoints: ['3 panduan awal', 'SSR HTML', 'CTA yang jelas'],
    cards: [
      { eyebrow: 'Tahan sensor', title: 'Cara melewati DPI dengan VLESS Reality tanpa merusak latensi', description: 'Deploy profil Reality yang tetap stabil di ISP yang agresif.' },
      { eyebrow: 'Operasi performa', title: 'Optimasi kecepatan VPN untuk streaming dan gaming', description: 'Kurangi latensi dengan menyelaraskan protokol dan wilayah keluar.' },
      { eyebrow: 'Operasi trust', title: 'Checklist rollout zero-log VPN untuk tim terdistribusi', description: 'Luncurkan VPN tim tanpa shadow IT dan asumsi logging yang kabur.' },
    ],
    ctaLinks: [
      { label: 'Bandingkan paket', description: 'Pilih paket dengan throughput dan slot perangkat yang cukup.' },
      { label: 'Unduh klien', description: 'Dapatkan klien untuk Android, iOS, desktop, dan stack berbasis sing-box.' },
      { label: 'Buka trust center', description: 'Tinjau posisi logging, kontrol infrastruktur, dan penanganan abuse.' },
    ],
  },
  'vi-VN': {
    badge: 'Sổ tay vận hành',
    title: 'Hướng dẫn VPN về thiết lập, tốc độ, vượt chặn và đánh giá độ tin cậy',
    description:
      'Đây là các trang kiến thức SSR dành cho người dùng đang so sánh kiến trúc VPN, xử lý mạng bị kiểm soát gắt gao và đánh giá liệu CyberVPN có đủ tin cậy để sử dụng thực tế hay không.',
    bullets: [
      'Nội dung bám sát search intent thực tế thay vì nhồi từ khóa.',
      'Tập trung vào thiết lập, hiệu năng, chống kiểm duyệt và trust operations.',
      'Mọi trang đều liên kết tới pricing, devices, docs, trust center và audit.',
    ],
    proofPoints: ['3 hướng dẫn khởi đầu', 'SSR HTML', 'CTA rõ ràng'],
    cards: [
      { eyebrow: 'Chống chặn', title: 'Cách vượt DPI với VLESS Reality mà không tăng độ trễ quá mức', description: 'Triển khai profile Reality đủ bền cho ISP bị kiểm soát mạnh.' },
      { eyebrow: 'Hiệu năng', title: 'Tối ưu tốc độ VPN cho streaming và gaming', description: 'Giảm độ trễ có thể tránh bằng cách chọn đúng giao thức và vùng mạng.' },
      { eyebrow: 'Trust operations', title: 'Checklist rollout zero-log VPN cho đội ngũ phân tán', description: 'Triển khai VPN cho team mà không tạo shadow IT hay onboarding yếu.' },
    ],
    ctaLinks: [
      { label: 'So sánh gói', description: 'Chọn gói có đủ băng thông và số lượng thiết bị.' },
      { label: 'Tải client', description: 'Nhận client cho Android, iOS, desktop và các stack dựa trên sing-box.' },
      { label: 'Mở trust center', description: 'Xem chính sách log, kiểm soát hạ tầng và cách xử lý abuse.' },
    ],
  },
  'th-TH': {
    badge: 'คู่มือการปฏิบัติการ',
    title: 'คู่มือ VPN สำหรับการตั้งค่า ความเร็ว การหลบ DPI และการประเมินความน่าเชื่อถือ',
    description:
      'หน้าเนื้อหาแบบ SSR สำหรับผู้ใช้ที่กำลังเปรียบเทียบสถาปัตยกรรม VPN แก้ปัญหาเครือข่ายที่เข้มงวด และประเมินว่า CyberVPN น่าเชื่อถือพอสำหรับการใช้งานจริงหรือไม่',
    bullets: [
      'เขียนตาม search intent จริง ไม่ใช่การยัดคีย์เวิร์ด',
      'เน้นการตั้งค่า ประสิทธิภาพ การต้านการบล็อก และ trust operations',
      'ทุกหน้าลิงก์ต่อไปยัง pricing, devices, docs, trust center และ audit',
    ],
    proofPoints: ['3 คู่มือเริ่มต้น', 'SSR HTML', 'CTA ชัดเจน'],
    cards: [
      { eyebrow: 'ต้านการบล็อก', title: 'วิธีหลบ DPI ด้วย VLESS Reality โดยไม่เพิ่ม latency เกินจำเป็น', description: 'ตั้งค่า Reality profile ที่ยังใช้งานได้บน ISP ที่เข้มงวด.' },
      { eyebrow: 'ประสิทธิภาพ', title: 'การปรับความเร็ว VPN สำหรับสตรีมมิงและเกม', description: 'ลด latency ที่ไม่จำเป็นด้วยการเลือกโปรโตคอลและ region ที่เหมาะสม.' },
      { eyebrow: 'ความเชื่อถือ', title: 'เช็กลิสต์ rollout ของ zero-log VPN สำหรับทีมกระจายตัว', description: 'เปิดใช้ VPN สำหรับทีมโดยไม่สร้าง shadow IT หรือ onboarding ที่อ่อนแอ.' },
    ],
    ctaLinks: [
      { label: 'เปรียบเทียบแพ็กเกจ', description: 'เลือกแพ็กเกจที่มี throughput และจำนวนอุปกรณ์เพียงพอ.' },
      { label: 'ดาวน์โหลดไคลเอนต์', description: 'รับไคลเอนต์สำหรับ Android, iOS, desktop และ stack ที่ใช้ sing-box.' },
      { label: 'เปิด trust center', description: 'ดูแนวทางเรื่อง logging การควบคุมโครงสร้างพื้นฐาน และการจัดการ abuse.' },
    ],
  },
  'ja-JP': {
    badge: '運用プレイブック',
    title: '設定、速度、検閲回避、信頼評価に答える VPN ガイド',
    description:
      'VPN アーキテクチャを比較し、厳しいネットワークを突破し、CyberVPN を実運用で信頼できるか判断したいユーザー向けの SSR ナレッジページです。',
    bullets: [
      '空虚なキーワードではなく実際の検索意図に合わせて構成。',
      'セットアップ、性能、検閲回避、トラスト運用に集中。',
      'pricing、devices、docs、trust center、audit へ内部リンク済み。',
    ],
    proofPoints: ['3 本の初期ガイド', 'SSR HTML', '明確な CTA'],
    cards: [
      { eyebrow: '検閲回避', title: 'VLESS Reality で DPI を低遅延のまま回避する方法', description: '厳しい ISP でも使える Reality プロファイルを構築します。' },
      { eyebrow: '性能運用', title: 'ストリーミングとゲーム向けの VPN 速度最適化', description: 'プロトコルとリージョン選択で不要な遅延を削減します。' },
      { eyebrow: '信頼運用', title: '分散チーム向け zero-log VPN ロールアウトチェックリスト', description: 'シャドー IT や曖昧なログ前提を避けて導入します。' },
    ],
    ctaLinks: [
      { label: '料金を比較', description: '必要なスループットとデバイス数を満たすプランを選択します。' },
      { label: 'クライアントを取得', description: 'Android、iOS、デスクトップ、sing-box 系クライアントを取得します。' },
      { label: 'トラストセンターを開く', description: 'ログ方針、インフラ制御、abuse 対応を確認します。' },
    ],
  },
  'ko-KR': {
    badge: '운영 플레이북',
    title: '설정, 속도, 검열 우회, 신뢰 평가를 다루는 VPN 가이드',
    description:
      'VPN 아키텍처를 비교하고, 강한 통제 네트워크 문제를 해결하며, CyberVPN을 실제 운영에 신뢰할 수 있는지 판단하려는 사용자를 위한 SSR 지식 페이지입니다.',
    bullets: [
      '비어 있는 키워드가 아니라 실제 검색 의도에 맞춰 작성했습니다.',
      '설정, 성능, 검열 회피, 트러스트 운영에 집중합니다.',
      'pricing, devices, docs, trust center, audit와 내부 링크로 연결됩니다.',
    ],
    proofPoints: ['초기 가이드 3개', 'SSR HTML', '명확한 CTA'],
    cards: [
      { eyebrow: '검열 회피', title: 'VLESS Reality로 지연을 크게 늘리지 않고 DPI를 우회하는 방법', description: '강한 ISP 환경에서도 유지되는 Reality 프로필을 구성합니다.' },
      { eyebrow: '성능 운영', title: '스트리밍과 게임을 위한 VPN 속도 최적화', description: '프로토콜과 지역 선택으로 불필요한 지연을 줄입니다.' },
      { eyebrow: '신뢰 운영', title: '분산 팀을 위한 zero-log VPN 롤아웃 체크리스트', description: '섀도 IT와 모호한 로깅 가정 없이 팀 VPN을 배포합니다.' },
    ],
    ctaLinks: [
      { label: '요금제 비교', description: '필요한 처리량과 기기 수를 충족하는 요금제를 선택합니다.' },
      { label: '클라이언트 다운로드', description: 'Android, iOS, 데스크톱 및 sing-box 기반 클라이언트를 받습니다.' },
      { label: '트러스트 센터 열기', description: '로그 정책, 인프라 제어, abuse 처리 방식을 검토합니다.' },
    ],
  },
};

export const COMPARE_HUB_LOCALIZATION: Partial<Record<SeoPriorityMarketLocale, LocalizedHubCopy>> = {
  'en-EN': {
    badge: 'Decision support',
    title: 'Protocol and client comparisons for users deciding between speed, stealth, and operational simplicity',
    description:
      'Comparison pages built to answer buyer and operator questions before they land in support, and to channel them toward the right download, plan, or trust surface.',
    bullets: [
      'Turns protocol selection into a concrete operating decision.',
      'Links comparison outcomes to pricing, downloads, trust, and help.',
      'Keeps content server-rendered and index-ready without client-side shells.',
    ],
    proofPoints: ['2 protocol comparisons', 'Server-rendered HTML', 'Clear CTA routing'],
    cards: [
      {
        eyebrow: 'Protocol comparison',
        title: 'VLESS Reality vs WireGuard: which one should carry your default VPN traffic',
        description:
          'Choose between censorship resistance and operational simplicity by mapping each protocol to the environments your users actually face.',
      },
      {
        eyebrow: 'Client stack comparison',
        title: 'sing-box vs Clash Meta for advanced routing and fallback control',
        description:
          'Compare the client stacks most advanced users consider when they need layered routing and clean fallback behavior.',
      },
    ],
    ctaLinks: [
      { label: 'Review full docs', description: 'Cross-check the protocol details before choosing a default stack.' },
      { label: 'Check pricing', description: 'Match performance goals and device counts to a practical plan.' },
      { label: 'Open help center', description: 'See the support surfaces available after rollout.' },
    ],
  },
  'ru-RU': {
    badge: 'Поддержка решения',
    title: 'Сравнения протоколов и клиентов для выбора между скоростью, маскировкой и простотой эксплуатации',
    description:
      'Comparison-страницы, которые отвечают на вопросы пользователя до обращения в поддержку и направляют его к правильному тарифу, загрузке или trust surface.',
    bullets: [
      'Переводят выбор протокола в конкретное операционное решение.',
      'Связывают результат сравнения с тарифами, загрузками, trust и help.',
      'Остаются server-rendered и индексируемыми без тяжёлой client-shell логики.',
    ],
    proofPoints: ['2 ключевых сравнения', 'SSR HTML', 'Понятные CTA'],
    cards: [
      { eyebrow: 'Сравнение протоколов', title: 'VLESS Reality vs WireGuard: что выбрать как основной VPN-трафик', description: 'Сравнение устойчивости к блокировкам и операционной простоты под реальные сценарии сети.' },
      { eyebrow: 'Сравнение клиентских стеков', title: 'sing-box vs Clash Meta для сложной маршрутизации и fallback-сценариев', description: 'Когда нужен rule-heavy routing, а когда важнее чистый deploy и предсказуемый fallback.' },
    ],
    ctaLinks: [
      { label: 'Открыть документацию', description: 'Сверьте детали протоколов до выбора базового стека.' },
      { label: 'Проверить тарифы', description: 'Соотнесите цели по скорости и количеству устройств с реальным тарифом.' },
      { label: 'Открыть help center', description: 'Посмотрите, как выглядит support surface после rollout.' },
    ],
  },
  'zh-CN': {
    badge: '决策支持',
    title: '帮助用户在速度、隐蔽性与运维复杂度之间做选择的协议与客户端对比',
    description:
      '这些对比页面用于在用户进入支持工单之前回答关键问题，并把他们导向合适的下载、套餐或信任页面。',
    bullets: [
      '把协议选择变成可执行的运营决策。',
      '把对比结果连接到价格、下载、信任与帮助页面。',
      '保持服务端渲染和可索引性，不依赖笨重的客户端壳层。',
    ],
    proofPoints: ['2 个核心对比', 'SSR HTML', '清晰 CTA'],
    cards: [
      { eyebrow: '协议对比', title: 'VLESS Reality vs WireGuard：默认 VPN 流量应该走哪一个', description: '根据用户真实网络环境比较抗审查能力与运维复杂度。' },
      { eyebrow: '客户端栈对比', title: 'sing-box vs Clash Meta：高级路由与回退控制怎么选', description: '在复杂规则生态与更干净的部署体验之间做判断。' },
    ],
    ctaLinks: [
      { label: '查看完整文档', description: '在决定默认协议栈之前先核对技术细节。' },
      { label: '查看套餐', description: '把性能目标和设备数量映射到合适的套餐。' },
      { label: '打开帮助中心', description: '了解上线后可用的支持路径。' },
    ],
  },
  'hi-IN': {
    badge: 'निर्णय सहायता',
    title: 'स्पीड, stealth और operational simplicity के बीच चुनने के लिए protocol और client comparisons',
    description:
      'ये comparison pages उपयोगकर्ता और operator के सवालों का जवाब support ticket बनने से पहले देने के लिए बनाई गई हैं.',
    bullets: [
      'Protocol selection को concrete operating decision में बदलती हैं.',
      'Comparison outcome को pricing, download, trust और help से जोड़ती हैं.',
      'Client shell के बिना SSR और index-ready output देती हैं.',
    ],
    proofPoints: ['2 मुख्य comparisons', 'SSR HTML', 'स्पष्ट CTA'],
    cards: [
      { eyebrow: 'Protocol comparison', title: 'VLESS Reality vs WireGuard: default VPN traffic किस पर चलना चाहिए', description: 'Network hostility और simplicity के आधार पर सही default चुनें.' },
      { eyebrow: 'Client stack comparison', title: 'Advanced routing के लिए sing-box vs Clash Meta', description: 'Layered routing और predictable fallback के लिए सही client stack चुनें.' },
    ],
    ctaLinks: [
      { label: 'पूरा docs देखें', description: 'Default stack चुनने से पहले protocol details verify करें.' },
      { label: 'प्राइसिंग देखें', description: 'Performance goals और device count को सही plan से मिलाएँ.' },
      { label: 'हेल्प सेंटर खोलें', description: 'Rollout के बाद उपलब्ध support surface देखें.' },
    ],
  },
  'id-ID': {
    badge: 'Dukungan keputusan',
    title: 'Perbandingan protokol dan klien untuk memilih antara kecepatan, stealth, dan kemudahan operasi',
    description:
      'Halaman perbandingan ini menjawab pertanyaan pembeli dan operator sebelum berubah menjadi tiket support.',
    bullets: [
      'Mengubah pemilihan protokol menjadi keputusan operasional yang nyata.',
      'Menghubungkan hasil perbandingan ke pricing, download, trust, dan help.',
      'Tetap SSR dan siap indeks tanpa shell klien yang berat.',
    ],
    proofPoints: ['2 perbandingan inti', 'SSR HTML', 'CTA jelas'],
    cards: [
      { eyebrow: 'Perbandingan protokol', title: 'VLESS Reality vs WireGuard: mana yang harus menjadi jalur VPN default', description: 'Tentukan default berdasarkan sensor, performa, dan biaya support.' },
      { eyebrow: 'Perbandingan stack klien', title: 'sing-box vs Clash Meta untuk routing lanjutan dan fallback', description: 'Bandingkan stack yang tepat untuk rule-heavy workflows atau deployment yang lebih bersih.' },
    ],
    ctaLinks: [
      { label: 'Baca docs lengkap', description: 'Cek detail protokol sebelum memilih stack default.' },
      { label: 'Lihat pricing', description: 'Cocokkan target performa dan jumlah perangkat ke plan yang tepat.' },
      { label: 'Buka help center', description: 'Lihat support surface yang tersedia setelah rollout.' },
    ],
  },
  'vi-VN': {
    badge: 'Hỗ trợ quyết định',
    title: 'So sánh giao thức và client để chọn giữa tốc độ, độ ẩn và độ đơn giản vận hành',
    description:
      'Các trang so sánh này trả lời câu hỏi của người mua và người vận hành trước khi chúng trở thành ticket hỗ trợ.',
    bullets: [
      'Biến lựa chọn giao thức thành quyết định vận hành cụ thể.',
      'Liên kết kết quả so sánh tới pricing, download, trust và help.',
      'Giữ SSR và index-ready mà không cần shell client nặng.',
    ],
    proofPoints: ['2 bài so sánh chính', 'SSR HTML', 'CTA rõ ràng'],
    cards: [
      { eyebrow: 'So sánh giao thức', title: 'VLESS Reality vs WireGuard: nên dùng gì cho lưu lượng VPN mặc định', description: 'Chọn theo mức độ kiểm duyệt, hiệu năng và chi phí hỗ trợ thực tế.' },
      { eyebrow: 'So sánh client stack', title: 'sing-box vs Clash Meta cho routing nâng cao và fallback', description: 'Khi nào cần hệ rule phức tạp và khi nào nên ưu tiên triển khai sạch hơn.' },
    ],
    ctaLinks: [
      { label: 'Xem docs đầy đủ', description: 'Đối chiếu chi tiết giao thức trước khi chọn stack mặc định.' },
      { label: 'Xem pricing', description: 'Khớp mục tiêu hiệu năng và số thiết bị với gói phù hợp.' },
      { label: 'Mở help center', description: 'Xem support surface có sẵn sau rollout.' },
    ],
  },
  'th-TH': {
    badge: 'ตัวช่วยตัดสินใจ',
    title: 'เปรียบเทียบโปรโตคอลและไคลเอนต์เพื่อเลือกระหว่างความเร็ว การพรางตัว และความง่ายในการดูแล',
    description:
      'หน้าเปรียบเทียบเหล่านี้ตอบคำถามของผู้ซื้อและผู้ดูแลก่อนที่จะกลายเป็น ticket ฝั่ง support.',
    bullets: [
      'เปลี่ยนการเลือกโปรโตคอลให้เป็นการตัดสินใจเชิงปฏิบัติการที่ชัดเจน',
      'เชื่อมผลการเปรียบเทียบไปยัง pricing, download, trust และ help',
      'คง SSR และพร้อมให้จัดทำดัชนีโดยไม่ต้องพึ่ง client shell หนัก ๆ',
    ],
    proofPoints: ['2 หน้าเปรียบเทียบหลัก', 'SSR HTML', 'CTA ชัดเจน'],
    cards: [
      { eyebrow: 'เปรียบเทียบโปรโตคอล', title: 'VLESS Reality vs WireGuard: อะไรควรเป็นเส้นทาง VPN หลัก', description: 'ตัดสินใจจากระดับการบล็อก ประสิทธิภาพ และต้นทุนการซัพพอร์ต.' },
      { eyebrow: 'เปรียบเทียบ client stack', title: 'sing-box vs Clash Meta สำหรับ routing ขั้นสูงและ fallback', description: 'เลือกให้เหมาะกับ rule-heavy workflow หรือ deployment ที่สะอาดกว่า.' },
    ],
    ctaLinks: [
      { label: 'อ่าน docs เต็ม', description: 'ตรวจสอบรายละเอียดโปรโตคอลก่อนเลือก stack หลัก.' },
      { label: 'ดูราคา', description: 'จับคู่เป้าหมายด้านประสิทธิภาพและจำนวนอุปกรณ์กับแพ็กเกจที่เหมาะสม.' },
      { label: 'เปิด help center', description: 'ดู support surface ที่มีหลัง rollout.' },
    ],
  },
  'ja-JP': {
    badge: '意思決定支援',
    title: '速度、秘匿性、運用のしやすさを比較するためのプロトコル・クライアント比較',
    description:
      '購入前や運用前の疑問に先回りして答え、適切なダウンロード、料金、トラストページへ導く比較ページです。',
    bullets: [
      'プロトコル選定を具体的な運用判断に変換します。',
      '比較結果を pricing、download、trust、help と接続します。',
      '重い client shell なしで SSR とインデックス対応を維持します。',
    ],
    proofPoints: ['主要比較 2 本', 'SSR HTML', '明確な CTA'],
    cards: [
      { eyebrow: 'プロトコル比較', title: 'VLESS Reality vs WireGuard: デフォルトの VPN トラフィックはどちらにすべきか', description: '検閲環境、性能、サポート負荷に基づいて判断します。' },
      { eyebrow: 'クライアントスタック比較', title: '高度なルーティングと fallback 制御のための sing-box vs Clash Meta', description: 'ルール重視か、クリーンな配布体験重視かを整理します。' },
    ],
    ctaLinks: [
      { label: '詳細ドキュメントを見る', description: 'デフォルトスタックを決める前にプロトコル詳細を確認します。' },
      { label: '料金を見る', description: '性能要件とデバイス数を適切なプランに合わせます。' },
      { label: 'ヘルプセンターを開く', description: 'ロールアウト後に使えるサポート面を確認します。' },
    ],
  },
  'ko-KR': {
    badge: '의사결정 지원',
    title: '속도, 은폐성, 운영 단순성 사이에서 선택하기 위한 프로토콜 및 클라이언트 비교',
    description:
      '구매 전과 운영 전의 질문을 지원 티켓으로 가기 전에 해결하고, 적절한 다운로드·요금제·트러스트 페이지로 연결하는 비교 페이지입니다.',
    bullets: [
      '프로토콜 선택을 구체적인 운영 결정으로 바꿉니다.',
      '비교 결과를 pricing, download, trust, help와 연결합니다.',
      '무거운 client shell 없이 SSR과 색인 준비 상태를 유지합니다.',
    ],
    proofPoints: ['핵심 비교 2개', 'SSR HTML', '명확한 CTA'],
    cards: [
      { eyebrow: '프로토콜 비교', title: 'VLESS Reality vs WireGuard: 기본 VPN 트래픽은 무엇을 써야 하는가', description: '검열 강도, 성능, 지원 비용을 기준으로 기본 경로를 결정합니다.' },
      { eyebrow: '클라이언트 스택 비교', title: '고급 라우팅과 fallback 제어를 위한 sing-box vs Clash Meta', description: '복잡한 규칙 생태계와 더 깔끔한 배포 경험 사이를 비교합니다.' },
    ],
    ctaLinks: [
      { label: '전체 문서 보기', description: '기본 스택을 정하기 전에 프로토콜 세부 정보를 확인합니다.' },
      { label: '요금 확인', description: '성능 목표와 기기 수를 적절한 요금제에 맞춥니다.' },
      { label: '헬프 센터 열기', description: '롤아웃 후 사용할 수 있는 지원 경로를 확인합니다.' },
    ],
  },
};

export const DEVICES_HUB_LOCALIZATION: Partial<Record<SeoPriorityMarketLocale, LocalizedHubCopy>> = {
  'en-EN': {
    badge: 'Setup playbooks',
    title: 'Device-specific VPN setup guides for Android, iPhone, iPad, and desktop clients',
    description:
      'Setup pages built to reduce support friction, align the right client to the right device, and move users toward working installs instead of generic troubleshooting loops.',
    bullets: [
      'Device-specific setup guidance with explicit fallback paths.',
      'Linked to download, help, compare, pricing, trust, and status surfaces.',
      'Structured as server-rendered acquisition pages instead of app-only flows.',
    ],
    proofPoints: ['3 setup guides', 'SoftwareApplication schema', 'Support-first linking'],
    cards: [
      { eyebrow: 'Android setup', title: 'Android VPN setup with CyberVPN for restrictive Wi-Fi and mobile data', description: 'Set up Android clients with a stable default route and a restrictive-network fallback.' },
      { eyebrow: 'iPhone and iPad setup', title: 'iOS VPN setup for stable roaming between home, work, and public hotspots', description: 'Build a clean iOS route with an obvious fallback when the network degrades.' },
      { eyebrow: 'Desktop setup', title: 'Windows VPN setup for workstations that need speed, fallback, and support clarity', description: 'Deploy workstation clients with clean packaging and a clear recovery path.' },
    ],
    ctaLinks: [
      { label: 'Open download center', description: 'Get the right client bundle before you start manual setup.' },
      { label: 'Review help center', description: 'Use support docs when onboarding users or replacing a device.' },
      { label: 'Compare protocols', description: 'Choose the tunnel model that matches the device constraints.' },
    ],
  },
  'ru-RU': {
    badge: 'Сценарии настройки',
    title: 'Гайды по настройке VPN для Android, iPhone, iPad и desktop-клиентов',
    description:
      'Setup-страницы, которые уменьшают нагрузку на поддержку, подбирают правильный клиент под устройство и ведут пользователя к рабочей установке, а не к бесконечному troubleshooting.',
    bullets: [
      'Пошаговая настройка под конкретное устройство и явные fallback-маршруты.',
      'Связки с download, help, compare, pricing, trust и status.',
      'Серверные acquisition-страницы вместо app-only flow.',
    ],
    proofPoints: ['3 setup-гайда', 'SoftwareApplication schema', 'Support-first linking'],
    cards: [
      { eyebrow: 'Настройка Android', title: 'Настройка VPN на Android для жёсткого Wi‑Fi и мобильных сетей', description: 'Соберите стабильный default route и fallback для агрессивных сетей.' },
      { eyebrow: 'Настройка iPhone и iPad', title: 'Настройка VPN на iOS для роуминга между домом, офисом и публичными точками', description: 'Постройте чистый iOS-маршрут с понятным резервным сценарием.' },
      { eyebrow: 'Настройка desktop', title: 'Настройка VPN на Windows для рабочих станций со скоростью и fallback-сценарием', description: 'Разверните desktop-клиент с предсказуемой упаковкой и recovery-путём.' },
    ],
    ctaLinks: [
      { label: 'Открыть download center', description: 'Скачайте правильный клиентский пакет до ручной настройки.' },
      { label: 'Открыть help center', description: 'Используйте support-документацию при онбординге и замене устройства.' },
      { label: 'Сравнить протоколы', description: 'Выберите tunneling-модель под ограничения конкретного устройства.' },
    ],
  },
  'zh-CN': {
    badge: '配置手册',
    title: '面向 Android、iPhone、iPad 与桌面客户端的设备 VPN 配置指南',
    description:
      '这些配置页面用于减少支持摩擦，让正确的客户端匹配正确的设备，并把用户导向真正可用的安装结果，而不是泛泛的故障排查。',
    bullets: [
      '按设备拆分的配置说明，并提供明确的 fallback 路径。',
      '连接到下载、帮助、对比、价格、信任与状态页面。',
      '作为服务端渲染的获客页面，而不是仅限应用内流程。',
    ],
    proofPoints: ['3 个配置指南', 'SoftwareApplication schema', '以支持为先的链接结构'],
    cards: [
      { eyebrow: 'Android 配置', title: 'Android VPN 配置：适用于受限 Wi‑Fi 和移动网络', description: '准备稳定的默认路由与受限网络备用路由。' },
      { eyebrow: 'iPhone 与 iPad 配置', title: 'iOS VPN 配置：适用于家庭、办公室与公共热点之间漫游', description: '构建干净的 iOS 路径，并为劣化网络准备明显的后备方案。' },
      { eyebrow: '桌面配置', title: 'Windows VPN 配置：面向需要速度、fallback 与支持清晰度的工作站', description: '以清晰的客户端打包和恢复路径部署桌面端。' },
    ],
    ctaLinks: [
      { label: '打开下载中心', description: '在手动配置前先获取正确的客户端包。' },
      { label: '查看帮助中心', description: '设备上线或更换时使用支持文档。' },
      { label: '比较协议', description: '根据设备限制选择合适的隧道模型。' },
    ],
  },
  'hi-IN': {
    badge: 'सेटअप प्लेबुक',
    title: 'Android, iPhone, iPad और desktop clients के लिए device-specific VPN setup guides',
    description:
      'ये setup pages support friction कम करने, सही client को सही device से जोड़ने और users को working install तक पहुँचाने के लिए बनाई गई हैं.',
    bullets: [
      'हर डिवाइस के लिए अलग setup guidance और साफ fallback paths.',
      'Download, help, compare, pricing, trust और status से जुड़ी हुई.',
      'App-only flow के बजाय SSR acquisition pages के रूप में बनी.',
    ],
    proofPoints: ['3 setup guides', 'SoftwareApplication schema', 'Support-first linking'],
    cards: [
      { eyebrow: 'Android setup', title: 'Restrictive Wi-Fi और mobile data के लिए Android VPN setup', description: 'Stable default route और fallback path के साथ Android setup करें.' },
      { eyebrow: 'iPhone और iPad setup', title: 'Home, work और hotspot roaming के लिए iOS VPN setup', description: 'एक साफ iOS route बनाएँ जिसमें fallback स्पष्ट हो.' },
      { eyebrow: 'Desktop setup', title: 'Speed और fallback clarity चाहने वाले workstations के लिए Windows VPN setup', description: 'Desktop client rollout को clean packaging और recovery path के साथ तैयार करें.' },
    ],
    ctaLinks: [
      { label: 'डाउनलोड सेंटर खोलें', description: 'Manual setup से पहले सही client bundle प्राप्त करें.' },
      { label: 'हेल्प सेंटर देखें', description: 'Onboarding या device replacement के समय support docs उपयोग करें.' },
      { label: 'प्रोटोकॉल तुलना देखें', description: 'Device constraints के अनुसार सही tunnel model चुनें.' },
    ],
  },
  'id-ID': {
    badge: 'Playbook setup',
    title: 'Panduan setup VPN per perangkat untuk Android, iPhone, iPad, dan klien desktop',
    description:
      'Halaman setup ini dirancang untuk mengurangi friksi support, mencocokkan klien yang tepat dengan perangkat yang tepat, dan mendorong pengguna menuju instalasi yang benar-benar bekerja.',
    bullets: [
      'Panduan setup spesifik perangkat dengan jalur fallback yang jelas.',
      'Terhubung ke download, help, compare, pricing, trust, dan status.',
      'Disusun sebagai halaman akuisisi SSR, bukan flow yang hanya hidup di aplikasi.',
    ],
    proofPoints: ['3 panduan setup', 'SoftwareApplication schema', 'Linking yang ramah support'],
    cards: [
      { eyebrow: 'Setup Android', title: 'Setup VPN Android untuk Wi-Fi ketat dan mobile data', description: 'Siapkan default route yang stabil dan fallback untuk jaringan agresif.' },
      { eyebrow: 'Setup iPhone dan iPad', title: 'Setup VPN iOS untuk roaming stabil antara rumah, kantor, dan hotspot', description: 'Bangun jalur iOS yang bersih dengan fallback yang jelas.' },
      { eyebrow: 'Setup desktop', title: 'Setup VPN Windows untuk workstation yang butuh kecepatan dan fallback', description: 'Deploy klien desktop dengan packaging dan recovery path yang rapi.' },
    ],
    ctaLinks: [
      { label: 'Buka download center', description: 'Ambil bundle klien yang benar sebelum setup manual.' },
      { label: 'Tinjau help center', description: 'Gunakan docs support saat onboarding atau mengganti perangkat.' },
      { label: 'Bandingkan protokol', description: 'Pilih model tunnel yang sesuai dengan batasan perangkat.' },
    ],
  },
  'vi-VN': {
    badge: 'Sổ tay thiết lập',
    title: 'Hướng dẫn thiết lập VPN theo từng thiết bị cho Android, iPhone, iPad và desktop',
    description:
      'Các trang setup này giúp giảm chi phí support, ghép đúng client với đúng thiết bị và đưa người dùng tới một cài đặt thực sự hoạt động.',
    bullets: [
      'Hướng dẫn riêng cho từng thiết bị với đường fallback rõ ràng.',
      'Liên kết tới download, help, compare, pricing, trust và status.',
      'Được xây dựng như các trang SSR phục vụ acquisition, không chỉ là flow trong app.',
    ],
    proofPoints: ['3 hướng dẫn setup', 'SoftwareApplication schema', 'Liên kết ưu tiên support'],
    cards: [
      { eyebrow: 'Thiết lập Android', title: 'Thiết lập VPN Android cho Wi-Fi bị kiểm soát và mạng di động', description: 'Chuẩn bị default route ổn định và fallback cho mạng khó.' },
      { eyebrow: 'Thiết lập iPhone và iPad', title: 'Thiết lập VPN iOS cho việc chuyển đổi giữa nhà, công ty và hotspot', description: 'Xây dựng tuyến iOS gọn gàng với fallback rõ ràng.' },
      { eyebrow: 'Thiết lập desktop', title: 'Thiết lập VPN Windows cho workstation cần tốc độ và fallback rõ ràng', description: 'Triển khai desktop client với packaging và recovery path sạch.' },
    ],
    ctaLinks: [
      { label: 'Mở download center', description: 'Lấy đúng bundle client trước khi cấu hình thủ công.' },
      { label: 'Xem help center', description: 'Dùng tài liệu support khi onboarding hoặc thay thiết bị.' },
      { label: 'So sánh giao thức', description: 'Chọn mô hình tunnel phù hợp với giới hạn của thiết bị.' },
    ],
  },
  'th-TH': {
    badge: 'คู่มือตั้งค่า',
    title: 'คู่มือตั้งค่า VPN ตามประเภทอุปกรณ์สำหรับ Android, iPhone, iPad และเดสก์ท็อป',
    description:
      'หน้า setup เหล่านี้ช่วยลดภาระฝั่ง support จับคู่ client ที่ถูกต้องกับอุปกรณ์ที่ถูกต้อง และพาผู้ใช้ไปสู่การติดตั้งที่ใช้งานได้จริง.',
    bullets: [
      'คำแนะนำแยกตามอุปกรณ์พร้อม fallback path ที่ชัดเจน.',
      'เชื่อมต่อกับ download, help, compare, pricing, trust และ status.',
      'สร้างเป็นหน้า SSR สำหรับ acquisition ไม่ใช่ flow ที่อยู่แค่ในแอป.',
    ],
    proofPoints: ['3 คู่มือตั้งค่า', 'SoftwareApplication schema', 'Linking ที่เน้น support'],
    cards: [
      { eyebrow: 'ตั้งค่า Android', title: 'ตั้งค่า VPN บน Android สำหรับ Wi‑Fi ที่เข้มงวดและเครือข่ายมือถือ', description: 'เตรียม default route ที่เสถียรและ fallback สำหรับเครือข่ายที่ยาก.' },
      { eyebrow: 'ตั้งค่า iPhone และ iPad', title: 'ตั้งค่า VPN บน iOS สำหรับการสลับระหว่างบ้าน ที่ทำงาน และ hotspot', description: 'สร้างเส้นทาง iOS ที่สะอาดและมี fallback ชัดเจน.' },
      { eyebrow: 'ตั้งค่าเดสก์ท็อป', title: 'ตั้งค่า VPN บน Windows สำหรับ workstation ที่ต้องการความเร็วและ fallback', description: 'Deploy desktop client ด้วย packaging และ recovery path ที่ชัดเจน.' },
    ],
    ctaLinks: [
      { label: 'เปิด download center', description: 'รับ bundle ไคลเอนต์ที่ถูกต้องก่อนเริ่มตั้งค่าด้วยตนเอง.' },
      { label: 'ดู help center', description: 'ใช้เอกสาร support ตอน onboarding หรือเปลี่ยนอุปกรณ์.' },
      { label: 'เปรียบเทียบโปรโตคอล', description: 'เลือก tunnel model ที่เหมาะกับข้อจำกัดของอุปกรณ์.' },
    ],
  },
  'ja-JP': {
    badge: 'セットアッププレイブック',
    title: 'Android、iPhone、iPad、デスクトップ向けのデバイス別 VPN セットアップガイド',
    description:
      'サポート負荷を減らし、正しいクライアントを正しいデバイスに合わせ、ユーザーを実際に動くセットアップへ導くためのページです。',
    bullets: [
      'デバイスごとのセットアップ手順と明確な fallback 経路。',
      'download、help、compare、pricing、trust、status と接続。',
      'アプリ内限定ではなく SSR の獲得ページとして構成。',
    ],
    proofPoints: ['セットアップガイド 3 本', 'SoftwareApplication schema', 'Support-first linking'],
    cards: [
      { eyebrow: 'Android 設定', title: '制限の強い Wi‑Fi とモバイル回線向け Android VPN 設定', description: '安定したデフォルト経路と制限ネットワーク用 fallback を準備します。' },
      { eyebrow: 'iPhone / iPad 設定', title: '自宅、職場、公共ホットスポットをまたぐ iOS VPN 設定', description: '明確な fallback を持つクリーンな iOS ルートを構築します。' },
      { eyebrow: 'デスクトップ設定', title: '速度と fallback が必要なワークステーション向け Windows VPN 設定', description: 'クリーンな配布と recovery path で desktop client を展開します。' },
    ],
    ctaLinks: [
      { label: 'ダウンロードセンターを開く', description: '手動設定の前に正しいクライアント bundle を取得します。' },
      { label: 'ヘルプセンターを見る', description: 'オンボーディングや端末交換時に support docs を使います。' },
      { label: 'プロトコルを比較', description: 'デバイス制約に合う tunnel model を選びます。' },
    ],
  },
  'ko-KR': {
    badge: '설정 플레이북',
    title: 'Android, iPhone, iPad, 데스크톱을 위한 기기별 VPN 설정 가이드',
    description:
      '지원 마찰을 줄이고, 올바른 클라이언트를 올바른 기기에 연결하며, 사용자를 실제로 동작하는 설치 상태로 이끌기 위한 설정 페이지입니다.',
    bullets: [
      '기기별 설정 안내와 명확한 fallback 경로.',
      'download, help, compare, pricing, trust, status와 연결.',
      '앱 내부 전용 흐름이 아니라 SSR 획득 페이지로 구성.',
    ],
    proofPoints: ['설정 가이드 3개', 'SoftwareApplication schema', 'Support-first linking'],
    cards: [
      { eyebrow: 'Android 설정', title: '제한적인 Wi‑Fi와 모바일 데이터를 위한 Android VPN 설정', description: '안정적인 기본 경로와 공격적인 네트워크용 fallback을 준비합니다.' },
      { eyebrow: 'iPhone / iPad 설정', title: '집, 회사, 공용 핫스팟 사이를 이동하는 iOS VPN 설정', description: '명확한 fallback이 있는 깔끔한 iOS 경로를 구성합니다.' },
      { eyebrow: '데스크톱 설정', title: '속도와 fallback이 필요한 워크스테이션용 Windows VPN 설정', description: '정돈된 배포와 recovery path로 desktop client를 전개합니다.' },
    ],
    ctaLinks: [
      { label: '다운로드 센터 열기', description: '수동 설정 전에 올바른 client bundle을 받습니다.' },
      { label: '헬프 센터 보기', description: '온보딩이나 기기 교체 시 support docs를 사용합니다.' },
      { label: '프로토콜 비교', description: '기기 제약에 맞는 tunnel model을 선택합니다.' },
    ],
  },
};

export const TRUST_PAGE_LOCALIZATION: Partial<Record<SeoPriorityMarketLocale, LocalizedKnowledgeCopy>> = {
  'en-EN': {
    badge: 'Trust center',
    title: 'CyberVPN trust center',
    description:
      'A single operational summary of how CyberVPN approaches logging, infrastructure control, abuse handling, audits, and customer-facing support.',
    heroPoints: [
      'Summarizes the trust posture in one crawlable page.',
      'Links trust claims to audits, security, help, and status evidence.',
      'Reduces friction for buyers, support teams, and AI answer engines.',
    ],
    sections: [
      {
        title: 'Logging and data minimization stance',
        paragraphs: [
          'CyberVPN presents data minimization as an operating constraint, not a vague adjective.',
          'This page makes it clear which data surfaces exist for billing, support, security, and abuse handling, and which ones do not.',
        ],
        bullets: [
          'Do not make logging claims that support workflows cannot defend.',
          'State the purpose of each retained data class in plain language.',
          'Keep one visible path for technical and policy questions.',
        ],
      },
      {
        title: 'Infrastructure and operational controls',
        paragraphs: [
          'A trust surface is only credible if it points to how access, deployment, and incident handling are controlled.',
          'Users deciding whether to buy or recommend the service need a short, inspectable answer here.',
        ],
      },
      {
        title: 'Proof surfaces and escalation paths',
        paragraphs: [
          'Trust claims should connect directly to audits, public incident visibility, and customer support escalation.',
          'This is the page that AI answer engines are most likely to cite when summarizing service credibility.',
        ],
      },
    ],
    relatedLinks: [
      { label: 'Audits', href: '/audits', description: 'Review assessment posture and evidence expectations.' },
      { label: 'Security', href: '/security', description: 'Operational hardening and infrastructure security overview.' },
      { label: 'Status', href: '/status', description: 'Public reliability and incident visibility surface.' },
    ],
    ctaLinks: [
      { label: 'Read audits', href: '/audits', description: 'Inspect the evidence trail behind our public trust claims.', seoCta: 'trust_audits', seoZone: 'trust_content' },
      { label: 'Review security posture', href: '/security', description: 'See the operational controls that support the trust model.', seoCta: 'trust_security', seoZone: 'trust_content' },
      { label: 'Open help center', href: '/help', description: 'Find the user-facing support surface behind the service.', seoCta: 'trust_help', seoZone: 'trust_content' },
    ],
  },
  'ru-RU': {
    badge: 'Trust center',
    title: 'Trust center CyberVPN',
    description:
      'Единая operational-сводка о том, как CyberVPN подходит к логированию, инфраструктурному контролю, abuse-handling, аудитам и поддержке пользователей.',
    heroPoints: [
      'Собирает trust-позицию на одной crawlable-странице.',
      'Связывает trust-claims с аудитами, security, help и status evidence.',
      'Снижает трение для покупателей, support-команд и AI answer engines.',
    ],
    sections: [
      {
        title: 'Позиция по логированию и минимизации данных',
        paragraphs: [
          'CyberVPN рассматривает минимизацию данных как операционное ограничение, а не как расплывчатый маркетинговый тезис.',
          'На странице должно быть ясно, какие данные используются для billing, support, security и abuse-handling, а какие нет.',
        ],
        bullets: [
          'Не обещайте то, что support-процессы не могут защитить на практике.',
          'Поясняйте назначение каждого retained data class простым языком.',
          'Держите один видимый канал для технических и policy-вопросов.',
        ],
      },
      {
        title: 'Инфраструктурный и операционный контроль',
        paragraphs: [
          'Trust-поверхность имеет смысл только тогда, когда она показывает, как контролируются доступ, деплой и incident-handling.',
          'Пользователю нужен короткий, проверяемый ответ, а не абстрактное обещание.',
        ],
      },
      {
        title: 'Поверхности доказательств и пути эскалации',
        paragraphs: [
          'Trust-claims должны вести к аудитам, публичной видимости инцидентов и support-эскалации.',
          'Именно эту страницу AI-системы чаще всего будут цитировать при оценке надёжности сервиса.',
        ],
      },
    ],
    relatedLinks: [
      { label: 'Аудиты', href: '/audits', description: 'Посмотрите позицию по аудитам и ожидания к доказательной базе.' },
      { label: 'Security', href: '/security', description: 'Обзор hardening-практик и инфраструктурной безопасности.' },
      { label: 'Status', href: '/status', description: 'Публичная поверхность надёжности и инцидентов.' },
    ],
    ctaLinks: [
      { label: 'Открыть аудиты', href: '/audits', description: 'Проверьте, какие evidence стоят за публичными trust-claims.', seoCta: 'trust_audits', seoZone: 'trust_content' },
      { label: 'Посмотреть security posture', href: '/security', description: 'Изучите операционные меры, которые поддерживают trust-модель.', seoCta: 'trust_security', seoZone: 'trust_content' },
      { label: 'Открыть help center', href: '/help', description: 'Перейдите к пользовательской support-поверхности сервиса.', seoCta: 'trust_help', seoZone: 'trust_content' },
    ],
  },
  'zh-CN': {
    badge: '信任中心',
    title: 'CyberVPN 信任中心',
    description:
      '用一页可抓取的页面总结 CyberVPN 如何处理日志、基础设施控制、abuse 处理、审计以及面向用户的支持体系。',
    heroPoints: [
      '把信任姿态集中到一页可索引页面中。',
      '把信任声明与审计、安全、帮助和状态证据连接起来。',
      '降低买家、支持团队和 AI 答案引擎的理解成本。',
    ],
    sections: [
      {
        title: '日志与数据最小化立场',
        paragraphs: [
          'CyberVPN 将数据最小化视为运营约束，而不是模糊的营销形容词。',
          '这页内容会明确说明哪些数据面用于计费、支持、安全和 abuse 处理，哪些不会被保留。',
        ],
        bullets: [
          '不要做出支持流程无法兑现的日志承诺。',
          '用清晰语言说明每类保留数据的用途。',
          '为技术和政策问题保留一个可见的入口。',
        ],
      },
      {
        title: '基础设施与运营控制',
        paragraphs: [
          '只有说明访问控制、部署流程和事件响应如何受控，信任页面才真正可信。',
          '用户需要的是可核查的简短答案，而不是空洞承诺。',
        ],
      },
      {
        title: '证据页面与升级路径',
        paragraphs: [
          '信任声明必须直接连接到审计、公开事件可见性和客户支持升级路径。',
          '这也是 AI 系统最可能引用来判断服务可信度的页面。',
        ],
      },
    ],
    relatedLinks: [
      { label: '审计', href: '/audits', description: '查看审计姿态与证据要求。' },
      { label: '安全', href: '/security', description: '查看基础设施安全与硬化概览。' },
      { label: '状态', href: '/status', description: '公开可见的可靠性与事件页面。' },
    ],
    ctaLinks: [
      { label: '查看审计', href: '/audits', description: '检查我们的公开信任声明背后的证据路径。', seoCta: 'trust_audits', seoZone: 'trust_content' },
      { label: '查看安全姿态', href: '/security', description: '了解支撑信任模型的运营控制。', seoCta: 'trust_security', seoZone: 'trust_content' },
      { label: '打开帮助中心', href: '/help', description: '查看面向用户的支持页面。', seoCta: 'trust_help', seoZone: 'trust_content' },
    ],
  },
  'hi-IN': {
    badge: 'ट्रस्ट सेंटर',
    title: 'CyberVPN ट्रस्ट सेंटर',
    description:
      'एक ही crawlable पेज में यह बताता है कि CyberVPN logging, infrastructure control, abuse handling, audits और user-facing support को कैसे संभालता है.',
    heroPoints: [
      'एक ही पेज में trust posture का सार देता है.',
      'Trust claims को audits, security, help और status evidence से जोड़ता है.',
      'Buyers, support teams और AI engines के लिए friction कम करता है.',
    ],
    sections: [
      {
        title: 'Logging और data minimization stance',
        paragraphs: [
          'CyberVPN data minimization को marketing adjective नहीं, बल्कि operational constraint की तरह देखता है.',
          'यह पेज स्पष्ट करता है कि billing, support, security और abuse handling के लिए कौन-से data surfaces मौजूद हैं.',
        ],
        bullets: [
          'ऐसे logging claims न करें जिन्हें support workflows साबित न कर सकें.',
          'हर retained data class का उद्देश्य plain language में बताएँ.',
          'Technical और policy सवालों के लिए एक visible path रखें.',
        ],
      },
      {
        title: 'Infrastructure और operational controls',
        paragraphs: [
          'Trust surface तभी credible है जब वह access, deployment और incident handling controls को स्पष्ट करे.',
          'यहाँ उपयोगकर्ता को inspectable उत्तर चाहिए, vague promise नहीं.',
        ],
      },
      {
        title: 'Proof surfaces और escalation paths',
        paragraphs: [
          'Trust claims को audits, public incident visibility और support escalation से सीधे जुड़ना चाहिए.',
          'AI answer systems service credibility का सार निकालते समय इसी पेज को cite कर सकते हैं.',
        ],
      },
    ],
    relatedLinks: [
      { label: 'ऑडिट', href: '/audits', description: 'Assessment posture और evidence expectations देखें.' },
      { label: 'सिक्योरिटी', href: '/security', description: 'Operational hardening और infrastructure security overview.' },
      { label: 'स्टेटस', href: '/status', description: 'Public reliability और incident visibility surface.' },
    ],
    ctaLinks: [
      { label: 'ऑडिट पढ़ें', href: '/audits', description: 'हमारे public trust claims के पीछे evidence trail देखें.', seoCta: 'trust_audits', seoZone: 'trust_content' },
      { label: 'Security posture देखें', href: '/security', description: 'Trust model को support करने वाले operational controls देखें.', seoCta: 'trust_security', seoZone: 'trust_content' },
      { label: 'Help center खोलें', href: '/help', description: 'Service के user-facing support surface तक पहुँचें.', seoCta: 'trust_help', seoZone: 'trust_content' },
    ],
  },
  'id-ID': {
    badge: 'Pusat kepercayaan',
    title: 'Pusat kepercayaan CyberVPN',
    description:
      'Ringkasan crawlable tunggal tentang bagaimana CyberVPN menangani logging, kontrol infrastruktur, abuse handling, audit, dan support untuk pengguna.',
    heroPoints: [
      'Merangkum posture trust dalam satu halaman yang bisa dirayapi.',
      'Menghubungkan trust claims ke audit, security, help, dan bukti status.',
      'Mengurangi friksi bagi pembeli, tim support, dan mesin jawaban AI.',
    ],
    sections: [
      {
        title: 'Sikap logging dan minimisasi data',
        paragraphs: [
          'CyberVPN memperlakukan minimisasi data sebagai batasan operasional, bukan sekadar kata pemasaran.',
          'Halaman ini menjelaskan data apa yang ada untuk billing, support, security, dan abuse handling, dan apa yang tidak ada.',
        ],
        bullets: [
          'Jangan membuat klaim logging yang workflow support tidak bisa pertahankan.',
          'Jelaskan tujuan setiap retained data class dengan bahasa yang jelas.',
          'Sediakan satu jalur yang terlihat untuk pertanyaan teknis dan kebijakan.',
        ],
      },
      {
        title: 'Kontrol infrastruktur dan operasi',
        paragraphs: [
          'Surface trust hanya kredibel jika menunjukkan bagaimana akses, deployment, dan incident handling dikendalikan.',
          'Pengguna membutuhkan jawaban singkat yang bisa diperiksa, bukan janji kabur.',
        ],
      },
      {
        title: 'Surface bukti dan jalur eskalasi',
        paragraphs: [
          'Trust claims harus terhubung langsung ke audit, visibilitas insiden publik, dan eskalasi support.',
          'Halaman ini juga paling mungkin dirujuk oleh sistem AI saat menilai kredibilitas layanan.',
        ],
      },
    ],
    relatedLinks: [
      { label: 'Audit', href: '/audits', description: 'Tinjau posture assessment dan ekspektasi evidensi.' },
      { label: 'Security', href: '/security', description: 'Ringkasan hardening operasional dan keamanan infrastruktur.' },
      { label: 'Status', href: '/status', description: 'Surface publik untuk reliabilitas dan visibilitas insiden.' },
    ],
    ctaLinks: [
      { label: 'Baca audit', href: '/audits', description: 'Periksa jejak evidensi di balik trust claims publik kami.', seoCta: 'trust_audits', seoZone: 'trust_content' },
      { label: 'Lihat security posture', href: '/security', description: 'Pelajari kontrol operasional yang mendukung model trust.', seoCta: 'trust_security', seoZone: 'trust_content' },
      { label: 'Buka help center', href: '/help', description: 'Akses surface support yang dihadapi pengguna.', seoCta: 'trust_help', seoZone: 'trust_content' },
    ],
  },
  'vi-VN': {
    badge: 'Trung tâm tin cậy',
    title: 'Trung tâm tin cậy CyberVPN',
    description:
      'Một trang crawlable duy nhất tóm tắt cách CyberVPN xử lý logging, kiểm soát hạ tầng, abuse handling, audit và support hướng tới người dùng.',
    heroPoints: [
      'Tóm tắt trust posture trong một trang có thể được thu thập dữ liệu.',
      'Liên kết trust claims với audit, security, help và bằng chứng từ status.',
      'Giảm friction cho người mua, đội support và AI answer engines.',
    ],
    sections: [
      {
        title: 'Lập trường về logging và tối thiểu hóa dữ liệu',
        paragraphs: [
          'CyberVPN xem tối thiểu hóa dữ liệu là ràng buộc vận hành chứ không phải khẩu hiệu marketing.',
          'Trang này làm rõ dữ liệu nào tồn tại cho billing, support, security và abuse handling, và dữ liệu nào không.',
        ],
        bullets: [
          'Không đưa ra logging claims mà workflow support không thể bảo vệ.',
          'Giải thích mục đích của từng retained data class bằng ngôn ngữ rõ ràng.',
          'Giữ một lối vào hiển thị cho câu hỏi kỹ thuật và policy.',
        ],
      },
      {
        title: 'Kiểm soát hạ tầng và vận hành',
        paragraphs: [
          'Trang trust chỉ đáng tin khi nó chỉ ra cách kiểm soát truy cập, triển khai và incident handling.',
          'Người dùng cần câu trả lời ngắn gọn có thể kiểm tra, không phải lời hứa mơ hồ.',
        ],
      },
      {
        title: 'Bề mặt bằng chứng và đường leo thang',
        paragraphs: [
          'Trust claims phải dẫn trực tiếp tới audit, hiển thị sự cố công khai và đường leo thang support.',
          'Đây cũng là trang mà AI systems dễ trích dẫn nhất khi tóm tắt độ tin cậy của dịch vụ.',
        ],
      },
    ],
    relatedLinks: [
      { label: 'Kiểm toán', href: '/audits', description: 'Xem posture kiểm toán và kỳ vọng về bằng chứng.' },
      { label: 'Bảo mật', href: '/security', description: 'Tổng quan hardening vận hành và an ninh hạ tầng.' },
      { label: 'Trạng thái', href: '/status', description: 'Bề mặt công khai cho độ ổn định và hiển thị sự cố.' },
    ],
    ctaLinks: [
      { label: 'Đọc kiểm toán', href: '/audits', description: 'Kiểm tra chuỗi bằng chứng phía sau các trust claims công khai.', seoCta: 'trust_audits', seoZone: 'trust_content' },
      { label: 'Xem security posture', href: '/security', description: 'Tìm hiểu các kiểm soát vận hành hỗ trợ trust model.', seoCta: 'trust_security', seoZone: 'trust_content' },
      { label: 'Mở help center', href: '/help', description: 'Truy cập surface hỗ trợ hướng tới người dùng.', seoCta: 'trust_help', seoZone: 'trust_content' },
    ],
  },
  'th-TH': {
    badge: 'ศูนย์ความน่าเชื่อถือ',
    title: 'ศูนย์ความน่าเชื่อถือของ CyberVPN',
    description:
      'หน้า crawlable เดียวที่สรุปว่า CyberVPN จัดการ logging, การควบคุมโครงสร้างพื้นฐาน, abuse handling, audit และ support สำหรับผู้ใช้อย่างไร',
    heroPoints: [
      'สรุป trust posture ไว้ในหน้าเดียวที่ crawl ได้',
      'เชื่อม trust claims เข้ากับ audit, security, help และหลักฐานจาก status',
      'ลด friction สำหรับผู้ซื้อ ทีม support และ AI answer engines',
    ],
    sections: [
      {
        title: 'แนวทางเรื่อง logging และการลดข้อมูลให้น้อยที่สุด',
        paragraphs: [
          'CyberVPN มองการลดข้อมูลเป็นข้อจำกัดเชิงปฏิบัติการ ไม่ใช่คำโฆษณา.',
          'หน้านี้อธิบายชัดว่ามี data surfaces ใดบ้างสำหรับ billing, support, security และ abuse handling และไม่มีอะไรบ้าง.',
        ],
        bullets: [
          'อย่าให้คำมั่นเรื่อง logging ที่ workflow ฝั่ง support ไม่สามารถปกป้องได้จริง.',
          'อธิบายวัตถุประสงค์ของ retained data class แต่ละชนิดด้วยภาษาที่ชัดเจน.',
          'มีช่องทางที่มองเห็นได้สำหรับคำถามด้านเทคนิคและ policy.',
        ],
      },
      {
        title: 'การควบคุมโครงสร้างพื้นฐานและการปฏิบัติการ',
        paragraphs: [
          'Trust surface จะน่าเชื่อถือก็ต่อเมื่อชี้ให้เห็นว่าการเข้าถึง การ deploy และ incident handling ถูกควบคุมอย่างไร.',
          'ผู้ใช้ต้องการคำตอบสั้น ๆ ที่ตรวจสอบได้ ไม่ใช่คำสัญญาที่คลุมเครือ.',
        ],
      },
      {
        title: 'พื้นผิวหลักฐานและเส้นทางการยกระดับ',
        paragraphs: [
          'Trust claims ควรเชื่อมตรงไปยัง audit, การมองเห็น incident แบบสาธารณะ และเส้นทาง escalation ของ support.',
          'หน้านี้ยังเป็นหน้าที่ AI systems มีแนวโน้มจะอ้างอิงมากที่สุดเมื่อสรุปความน่าเชื่อถือของบริการ.',
        ],
      },
    ],
    relatedLinks: [
      { label: 'การตรวจสอบ', href: '/audits', description: 'ดูท่าทีด้านการตรวจสอบและความคาดหวังเรื่องหลักฐาน.' },
      { label: 'ความปลอดภัย', href: '/security', description: 'ภาพรวมด้าน hardening เชิงปฏิบัติการและความปลอดภัยโครงสร้างพื้นฐาน.' },
      { label: 'สถานะ', href: '/status', description: 'พื้นผิวสาธารณะสำหรับความเสถียรและการมองเห็น incident.' },
    ],
    ctaLinks: [
      { label: 'อ่าน audit', href: '/audits', description: 'ตรวจสอบเส้นทางหลักฐานเบื้องหลัง trust claims สาธารณะของเรา.', seoCta: 'trust_audits', seoZone: 'trust_content' },
      { label: 'ดู security posture', href: '/security', description: 'เรียนรู้การควบคุมเชิงปฏิบัติการที่รองรับ trust model.', seoCta: 'trust_security', seoZone: 'trust_content' },
      { label: 'เปิด help center', href: '/help', description: 'เข้าถึงพื้นผิว support ที่ผู้ใช้มองเห็นได้.', seoCta: 'trust_help', seoZone: 'trust_content' },
    ],
  },
  'ja-JP': {
    badge: 'トラストセンター',
    title: 'CyberVPN トラストセンター',
    description:
      'CyberVPN が logging、インフラ制御、abuse 対応、監査、ユーザー向け support をどう扱うかを 1 ページでまとめた crawlable ページです。',
    heroPoints: [
      'トラスト姿勢を 1 ページに集約します。',
      'トラスト主張を audit、security、help、status の証拠と接続します。',
      '購入検討者、support team、AI engine の理解コストを下げます。',
    ],
    sections: [
      {
        title: 'logging とデータ最小化の方針',
        paragraphs: [
          'CyberVPN はデータ最小化をマーケティング用語ではなく運用上の制約として扱います。',
          'このページでは billing、support、security、abuse handling に必要な data surface と不要なものを明確にします。',
        ],
        bullets: [
          'support workflow が守れない logging claims は行わない。',
          '各 retained data class の目的を平易に説明する。',
          '技術・policy 問い合わせの見える入口を 1 つ持つ。',
        ],
      },
      {
        title: 'インフラと運用の制御',
        paragraphs: [
          'アクセス制御、deploy、incident handling がどう管理されるかを示してこそ trust surface は信頼できます。',
          'ここで必要なのは検証可能な短い回答であり、曖昧な約束ではありません。',
        ],
      },
      {
        title: '証拠ページと escalation 経路',
        paragraphs: [
          'トラスト主張は audit、公開 incident visibility、support escalation に直接つながる必要があります。',
          'サービスの信頼性を要約する際、AI systems が最も参照しやすいページでもあります。',
        ],
      },
    ],
    relatedLinks: [
      { label: '監査', href: '/audits', description: '監査姿勢と必要な証拠を確認します。' },
      { label: 'セキュリティ', href: '/security', description: '運用 hardening とインフラ security の概要です。' },
      { label: 'ステータス', href: '/status', description: '公開 reliability と incident visibility のページです。' },
    ],
    ctaLinks: [
      { label: '監査を見る', href: '/audits', description: '公開 trust claims の裏にある証拠経路を確認します。', seoCta: 'trust_audits', seoZone: 'trust_content' },
      { label: 'security posture を確認', href: '/security', description: 'トラストモデルを支える運用制御を確認します。', seoCta: 'trust_security', seoZone: 'trust_content' },
      { label: 'ヘルプセンターを開く', href: '/help', description: 'ユーザー向け support surface に進みます。', seoCta: 'trust_help', seoZone: 'trust_content' },
    ],
  },
  'ko-KR': {
    badge: '트러스트 센터',
    title: 'CyberVPN 트러스트 센터',
    description:
      'CyberVPN이 logging, 인프라 제어, abuse 처리, 감사, 사용자 지원을 어떻게 다루는지 한 페이지로 요약한 crawlable 페이지입니다.',
    heroPoints: [
      '트러스트 포지션을 한 페이지에 요약합니다.',
      '트러스트 주장과 audit, security, help, status 증거를 연결합니다.',
      '구매자, 지원팀, AI 엔진의 이해 비용을 낮춥니다.',
    ],
    sections: [
      {
        title: 'logging 및 데이터 최소화 입장',
        paragraphs: [
          'CyberVPN은 데이터 최소화를 마케팅 문구가 아니라 운영 제약으로 취급합니다.',
          '이 페이지는 billing, support, security, abuse handling에 필요한 data surface와 그렇지 않은 부분을 명확히 설명합니다.',
        ],
        bullets: [
          'support workflow가 지킬 수 없는 logging claims는 하지 않습니다.',
          '각 retained data class의 목적을 쉬운 언어로 설명합니다.',
          '기술 및 policy 질문을 위한 보이는 경로를 하나 유지합니다.',
        ],
      },
      {
        title: '인프라 및 운영 통제',
        paragraphs: [
          '접근, 배포, incident handling이 어떻게 통제되는지 보여줘야 trust surface가 신뢰를 얻습니다.',
          '사용자에게 필요한 것은 모호한 약속이 아니라 점검 가능한 짧은 답변입니다.',
        ],
      },
      {
        title: '증거 페이지와 escalation 경로',
        paragraphs: [
          '트러스트 주장은 audit, 공개 incident visibility, support escalation과 직접 연결돼야 합니다.',
          '서비스 신뢰성을 요약할 때 AI systems가 가장 쉽게 참조할 수 있는 페이지이기도 합니다.',
        ],
      },
    ],
    relatedLinks: [
      { label: '감사', href: '/audits', description: '감사 포지션과 필요한 증거를 검토합니다.' },
      { label: '보안', href: '/security', description: '운영 hardening 및 인프라 security 개요입니다.' },
      { label: '상태', href: '/status', description: '공개 reliability 및 incident visibility 페이지입니다.' },
    ],
    ctaLinks: [
      { label: '감사 보기', href: '/audits', description: '공개 trust claims 뒤의 증거 경로를 검토합니다.', seoCta: 'trust_audits', seoZone: 'trust_content' },
      { label: 'security posture 확인', href: '/security', description: 'trust model을 지탱하는 운영 통제를 확인합니다.', seoCta: 'trust_security', seoZone: 'trust_content' },
      { label: '헬프 센터 열기', href: '/help', description: '사용자-facing support surface로 이동합니다.', seoCta: 'trust_help', seoZone: 'trust_content' },
    ],
  },
};

export const AUDITS_PAGE_LOCALIZATION: Partial<Record<SeoPriorityMarketLocale, LocalizedKnowledgeCopy>> = {
  'en-EN': {
    badge: 'Audit posture',
    title: 'CyberVPN audit and verification posture',
    description:
      'A public audit-facing summary of how CyberVPN intends to expose evidence, what external verification should cover, and how customers should evaluate claims responsibly.',
    heroPoints: [
      'Frames what independent verification should inspect.',
      'Connects evidence expectations to trust, security, and status surfaces.',
      'Gives buyers and AI systems a specific page to cite instead of guessing.',
    ],
    sections: [
      {
        title: 'What an audit should answer',
        paragraphs: [
          'An audit page should explain what independent review must verify for the service to deserve trust.',
          'That includes retention boundaries, infrastructure access controls, route integrity, and incident response behavior.',
        ],
      },
      {
        title: 'How to evaluate evidence quality',
        paragraphs: [
          'Screenshots and vague claims are not evidence. Customers need to know whether they are reading a real scope, a summary, or a marketing proxy.',
          'This page exists to reduce the risk of weak trust theater being mistaken for verification.',
        ],
        bullets: [
          'State the scope and date clearly.',
          'Explain what was out of scope.',
          'Tie remediation status back to public trust and security updates.',
        ],
      },
      {
        title: 'How audits feed operations',
        paragraphs: [
          'The value of an audit is whether findings change deployment and support behavior.',
          'That is why this page links directly into trust, security, and status instead of living as an isolated artifact.',
        ],
      },
    ],
    relatedLinks: [
      { label: 'Trust center', href: '/trust', description: 'Operational summary of how claims translate into practice.' },
      { label: 'Help center', href: '/help', description: 'User-facing surface for support and escalation.' },
      { label: 'Contact', href: '/contact', description: 'Route diligence questions to the team directly.' },
    ],
    ctaLinks: [
      { label: 'Open trust center', href: '/trust', description: 'Review the broader trust posture around audits and operations.', seoCta: 'audits_trust', seoZone: 'audits_content' },
      { label: 'Check status page', href: '/status', description: 'See how incident visibility ties into service reliability.', seoCta: 'audits_status', seoZone: 'audits_content' },
      { label: 'Contact team', href: '/contact', description: 'Ask operational or due-diligence questions directly.', seoCta: 'audits_contact', seoZone: 'audits_content' },
    ],
  },
  'ru-RU': {
    badge: 'Позиция по аудитам',
    title: 'Позиция CyberVPN по аудитам и внешней верификации',
    description:
      'Публичная audit-facing страница о том, какие evidence CyberVPN должен показывать, что должна покрывать внешняя проверка и как пользователю оценивать trust-claims без маркетингового шума.',
    heroPoints: [
      'Показывает, что именно должна проверять независимая верификация.',
      'Связывает ожидания к evidence с trust, security и status surface.',
      'Даёт пользователям и AI-системам конкретную страницу для цитирования.',
    ],
    sections: [
      {
        title: 'На какие вопросы должен отвечать аудит',
        paragraphs: [
          'Страница про аудиты не должна имитировать проверку, которой не было. Она должна объяснять, что именно обязана подтвердить независимая оценка.',
          'Речь идёт о границах хранения данных, инфраструктурном доступе, целостности маршрутов и поведении в incident response.',
        ],
      },
      {
        title: 'Как оценивать качество доказательств',
        paragraphs: [
          'Скриншоты и брендовые обещания не равны evidence. Пользователь должен видеть, это реальный scope, summary или маркетинговый proxy.',
          'Цель страницы — снизить риск того, что trust theater будет принят за реальную верификацию.',
        ],
        bullets: [
          'Ясно указывайте scope и дату оценки.',
          'Объясняйте, что осталось вне scope.',
          'Привязывайте remediation status к публичным trust и security updates.',
        ],
      },
      {
        title: 'Как аудит влияет на операции',
        paragraphs: [
          'Ценность аудита не в PDF, а в том, меняет ли он deploy и support-поведение.',
          'Поэтому страница связана с trust, security и status, а не живёт как изолированный артефакт.',
        ],
      },
    ],
    relatedLinks: [
      { label: 'Центр доверия', href: '/trust', description: 'Короткая operational-сводка о том, как claims переводятся в практику.' },
      { label: 'Help center', href: '/help', description: 'Пользовательская поверхность для поддержки и эскалации.' },
      { label: 'Контакты', href: '/contact', description: 'Задайте вопросы по due diligence напрямую команде.' },
    ],
    ctaLinks: [
      { label: 'Открыть trust center', href: '/trust', description: 'Посмотрите общую trust-позицию вокруг аудитов и операций.', seoCta: 'audits_trust', seoZone: 'audits_content' },
      { label: 'Открыть status page', href: '/status', description: 'Проверьте, как публичная видимость инцидентов связана с надёжностью сервиса.', seoCta: 'audits_status', seoZone: 'audits_content' },
      { label: 'Связаться с командой', href: '/contact', description: 'Задайте операционные и due-diligence вопросы напрямую.', seoCta: 'audits_contact', seoZone: 'audits_content' },
    ],
  },
  'zh-CN': {
    badge: '审计姿态',
    title: 'CyberVPN 审计与外部验证姿态',
    description:
      '这是一页面向审计的公开说明，解释 CyberVPN 应如何公开证据、外部验证应覆盖什么，以及用户应如何负责任地评估这些声明。',
    heroPoints: [
      '明确独立验证应该检查什么。',
      '把证据要求连接到 trust、security 与 status 页面。',
      '给买家和 AI 系统一个明确可引用的页面，而不是让它们自行猜测。',
    ],
    sections: [
      {
        title: '审计应该回答什么',
        paragraphs: [
          '审计页面不应伪装成不存在的评估，而应说明独立审查必须验证哪些事项，服务才值得信任。',
          '这包括数据保留边界、基础设施访问控制、路由完整性以及事件响应行为。',
        ],
      },
      {
        title: '如何评估证据质量',
        paragraphs: [
          '截图和品牌式承诺并不是证据。用户应知道自己看到的是实际审计范围、摘要，还是营销替代品。',
          '这页的存在是为了降低脆弱的 trust theater 被误认成验证结果的风险。',
        ],
        bullets: [
          '明确写出审计范围与日期。',
          '说明哪些内容不在范围内。',
          '把修复状态连接回公开的 trust 和 security 更新。',
        ],
      },
      {
        title: '审计如何反哺运营',
        paragraphs: [
          '审计的价值不在 PDF，而在于它是否改变了部署与支持行为。',
          '因此这页直接连接到 trust、security 与 status，而不是作为孤立文档存在。',
        ],
      },
    ],
    relatedLinks: [
      { label: '信任中心', href: '/trust', description: '查看声明如何落到实际运营中的总结页面。' },
      { label: '帮助中心', href: '/help', description: '面向用户的支持与升级路径页面。' },
      { label: '联系团队', href: '/contact', description: '直接向团队提出尽职调查问题。' },
    ],
    ctaLinks: [
      { label: '打开信任中心', href: '/trust', description: '查看围绕审计与运营的整体信任姿态。', seoCta: 'audits_trust', seoZone: 'audits_content' },
      { label: '查看状态页面', href: '/status', description: '了解公开事件可见性如何影响服务可靠性。', seoCta: 'audits_status', seoZone: 'audits_content' },
      { label: '联系团队', href: '/contact', description: '直接询问运营或尽职调查问题。', seoCta: 'audits_contact', seoZone: 'audits_content' },
    ],
  },
};
