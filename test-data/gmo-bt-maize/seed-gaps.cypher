// ============================================================================
// SEED GAP DETECTION — Story 4.4 (test trực quan UI gap mode)
// Chủ đề: Ngô biến đổi gen Bt × hệ vi sinh vật đất
//
// Tạo ĐÚNG 1 paper cho mỗi loại gap + 1 paper "sạch" (không cờ) để đối chứng:
//   - seed-contra   -> ĐỎ   (has_contradiction): có 2 finding CONTRADICTS nhau
//   - seed-isolated -> VÀNG (isolated_cluster):   không có cạnh CITES nào
//   - seed-unfilled -> VÀNG (unfilled_limitation): có Limitation chưa được FILLS_GAP
//   - seed-normal   -> KHÔNG MÀU: có CITES (không cô lập) + Limitation đã FILLS_GAP
//
// HƯỚNG DẪN:
//   1. Mở Neo4j Browser: http://localhost:7474  (neo4j / neo4jpassword)
//   2. Thay PROJECT_ID bằng id project thật của bạn (copy từ URL workspace)
//   3. Chạy cả block. Sang app -> tab Bản đồ tri thức -> reload -> "Tìm khoảng trống"
//   4. Dọn dẹp: chạy block CLEANUP ở cuối file
// ============================================================================

:param pid => 'PROJECT_ID';

// --- 1) MÂU THUẪN (đỏ): 2 finding trong cùng paper CONTRADICTS nhau ----------
MERGE (pc:Paper {id: 'seed-contra', project_id: $pid})
  SET pc.title = '[SEED] Ngô Bt và vi sinh vật đất: hai kết quả trái ngược';
MERGE (fc1:Finding {id: 'seed-fc1', project_id: $pid})
  SET fc1.description = 'Ngô Bt làm giảm đáng kể đa dạng vi sinh vật đất vùng rễ', fc1.confidence_score = 0.8;
MERGE (fc2:Finding {id: 'seed-fc2', project_id: $pid})
  SET fc2.description = 'Ngô Bt không gây khác biệt có ý nghĩa lên đa dạng vi sinh vật đất', fc2.confidence_score = 0.8;
MERGE (pc)-[:HAS_FINDING]->(fc1)
MERGE (pc)-[:HAS_FINDING]->(fc2)
MERGE (fc1)-[:CONTRADICTS]->(fc2);

// --- 2) CÔ LẬP (vàng): KHÔNG có cạnh CITES, KHÔNG limitation -----------------
MERGE (pi:Paper {id: 'seed-isolated', project_id: $pid})
  SET pi.title = '[SEED] Quy trình metagenomics định lượng vi sinh vật đất (độc lập)';

// --- 3) LIMITATION CHƯA GIẢI QUYẾT (vàng): có CITES (không cô lập) -----------
MERGE (pu:Paper {id: 'seed-unfilled', project_id: $pid})
  SET pu.title = '[SEED] Đánh giá ngắn hạn ngô Bt lên vi khuẩn cố định đạm';
MERGE (lu:Limitation {id: 'seed-lu', project_id: $pid})
  SET lu.description = 'Chỉ theo dõi 1 mùa vụ trong nhà kính, chưa đánh giá tác động tích lũy dài hạn ngoài đồng';
MERGE (pu)-[:HAS_LIMITATION]->(lu);
// (KHÔNG tạo FILLS_GAP cho lu -> đây chính là gap chưa được lấp)

// --- 4) PAPER SẠCH (không màu): có CITES + Limitation đã được FILLS_GAP -------
MERGE (pn:Paper {id: 'seed-normal', project_id: $pid})
  SET pn.title = '[SEED] Tổng quan dài hạn tác động ngô Bt lên hệ vi sinh đất';
MERGE (ln:Limitation {id: 'seed-ln', project_id: $pid})
  SET ln.description = 'Cần thêm dữ liệu thực địa đa vùng sinh thái';
MERGE (pn)-[:HAS_LIMITATION]->(ln)
MERGE (pn)-[:FILLS_GAP]->(ln);   // limitation đã được lấp -> KHÔNG tính unfilled

// --- CITES: để pc, pu, pn KHÔNG cô lập; chỉ pi cô lập -----------------------
MERGE (pc)-[:CITES]->(pn)
MERGE (pu)-[:CITES]->(pn)
MERGE (pn)-[:CITES]->(pc);

// ============================================================================
// KIỂM TRA NHANH (chạy riêng): kỳ vọng 3 dòng
//   seed-contra=has_contradiction, seed-isolated=isolated, seed-unfilled=unfilled
// ============================================================================
// MATCH (p:Paper {project_id:'PROJECT_ID'})
// OPTIONAL MATCH (p)-[:HAS_FINDING]->(:Finding)-[:CONTRADICTS]-(:Finding) WITH p, count(*) AS contra
// OPTIONAL MATCH (p)-[:CITES]-(:Paper) WITH p, contra, count(*) AS cites
// OPTIONAL MATCH (p)-[:HAS_LIMITATION]->(l:Limitation) WHERE NOT EXISTS { (:Paper)-[:FILLS_GAP]->(l) }
// WITH p, contra, cites, count(l) AS unfilled
// RETURN p.id, contra>0 AS red, (cites=0) AS isolated, unfilled>0 AS unfilled_gap ORDER BY p.id;

// ============================================================================
// CLEANUP — xóa toàn bộ seed (thay PROJECT_ID)
// ============================================================================
// MATCH (n) WHERE n.id STARTS WITH 'seed-' AND n.project_id = 'PROJECT_ID' DETACH DELETE n;
