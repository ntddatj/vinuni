export const translations = {
  'sidebar.createProject': { vi: '+ Tạo dự án mới', en: '+ Create Project' },
  'sidebar.projectList': { vi: 'Danh sách các dự án', en: 'Project List' },
  'sidebar.viewAll': { vi: 'Xem tất cả →', en: 'View all →' },
  'tab.library': { vi: 'Thư viện Tài liệu', en: 'Document Library' },
  'tab.graph': { vi: 'Bản đồ Tri thức', en: 'Knowledge Map' },
  'tab.writing': { vi: 'Hỗ trợ viết tổng quan', en: 'Overview Writing Support' },
  'chat.title': { vi: 'Trợ lý nghiên cứu', en: 'Research Assistant' },
  'chat.placeholder': { vi: 'Bạn cần tôi hỗ trợ gì...', en: 'How can I help you...' },
  'chat.hide': { vi: 'Ẩn Chat', en: 'Hide Chat' },
  'chat.show': { vi: 'Hiện Chat', en: 'Show Chat' },
  'header.settings': { vi: 'Cài đặt Hệ thống', en: 'System Settings' },
  'header.logout': { vi: 'Đăng xuất', en: 'Logout' },
  'map.title': { vi: 'BẢN ĐỒ TRI THỨC CYTOSCAPE.JS', en: 'CYTOSCAPE.JS KNOWLEDGE MAP' },
  'onboarding.createFirst': { vi: 'Tạo dự án đầu tiên của bạn', en: 'Create your first project' },
  'onboarding.guide': { vi: 'Hướng dẫn bắt đầu nhanh', en: 'Quick Start Guide' },
  'sidebar.rename': { vi: 'Đổi tên', en: 'Rename' },
  'sidebar.delete': { vi: 'Xóa', en: 'Delete' },
  'workspace.selectProject': { vi: 'Chọn một dự án', en: 'Select a project' },
  'chat.comingSoon': { vi: 'Chat sẽ được kích hoạt ở Epic 3.', en: 'Chat will be available in Epic 3.' },
} as const;

export type TranslationKey = keyof typeof translations;
