/* ===== HTTP 헬퍼 ===== */
async function fetchJson(url) {
  const response = await fetch(url);
  const json = await response.json();
  if (!response.ok) throw new Error(json.detail || "요청에 실패했습니다.");
  return json;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const json = await response.json();
  if (!response.ok) throw new Error(json.detail || "요청에 실패했습니다.");
  return json;
}

/* ===== XSS 방지 ===== */
function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/* ===== 날짜 포맷 ===== */
function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("ko-KR", { hour12: false });
}

function formatTime(value) {
  if (!value) return "-";
  return new Date(value).toLocaleTimeString("ko-KR", { hour12: false });
}

/* ===== 학부별 CSS 클래스 ===== */
function departmentClass(department) {
  const v = String(department || "");
  if (v.includes("미생물")) return "dept-micro";
  if (v.includes("요경검")) return "dept-urine";
  if (v.includes("분자진단")) return "dept-molecular";
  if (v.includes("진단혈액") || v.includes("혈액")) return "dept-hematology";
  if (v.includes("세포")) return "dept-cell";
  if (v.includes("임상화학")) return "dept-chemistry";
  if (v.includes("A/S")) return "dept-asfluor";
  if (v.includes("외주")) return "dept-outsource";
  if (v.includes("면역") || v.includes("혈청")) return "dept-immunology";
  return "dept-other";
}

/* 스캔 결과 칩용 — new CSS naming (dc-*) */
function departmentChipClass(department) {
  const v = String(department || "");
  if (v.includes("미생물")) return "dc-micro";
  if (v.includes("요경검")) return "dc-urine";
  if (v.includes("분자진단")) return "dc-molecular";
  if (v.includes("진단혈액") || v.includes("혈액")) return "dc-hematology";
  if (v.includes("세포")) return "dc-cell";
  if (v.includes("임상화학")) return "dc-chemistry";
  if (v.includes("A/S")) return "dc-asfluor";
  if (v.includes("외주")) return "dc-outsource";
  if (v.includes("면역") || v.includes("혈청")) return "dc-immunology";
  return "dc-other";
}

function departmentIcon(department) {
  const v = String(department || "");
  if (v.includes("미생물")) return "bi-virus2";
  if (v.includes("요경검")) return "bi-droplet-half";
  if (v.includes("분자진단")) return "bi-diagram-3";
  if (v.includes("진단혈액")) return "bi-droplet";
  if (v.includes("세포병리")) return "bi-circle-half";
  if (v.includes("세포")) return "bi-circle-half";
  if (v.includes("임상화학")) return "bi-flask";
  if (v.includes("A/S")) return "bi-lightbulb";
  if (v.includes("외주")) return "bi-truck";
  if (v.includes("면역") || v.includes("혈청")) return "bi-shield-check";
  return "bi-question-circle";
}

/* ===== 토스트 알림 ===== */
(function () {
  const stack = document.createElement("div");
  stack.className = "toast-stack";
  document.body.appendChild(stack);

  window.showToast = function (title, message, type = "success", duration = 3500) {
    const icons = {
      success: "bi-check-circle-fill",
      danger: "bi-x-circle-fill",
      warning: "bi-exclamation-triangle-fill",
    };
    const toast = document.createElement("div");
    toast.className = `app-toast toast-${type}`;
    toast.innerHTML = `
      <i class="bi ${icons[type] || "bi-info-circle-fill"}"></i>
      <div class="toast-body">
        <div class="toast-title">${escapeHtml(title)}</div>
        <div class="toast-msg">${escapeHtml(message)}</div>
      </div>`;
    stack.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("toast-fade-out");
      setTimeout(() => toast.remove(), 350);
    }, duration);
  };
})();

/* ===== 실시간 시계 ===== */
(function () {
  const el = document.getElementById("realtimeClock");
  if (!el) return;
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleString("ko-KR", {
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false,
    });
  }
  tick();
  setInterval(tick, 1000);
})();

/* ===== 스캔 결과 렌더러 ===== */
function renderScanResult(data) {
  const statusOk    = data.order_found;
  const patientText = `${data.patient_name || "-"}${data.patient_age ? ` / ${data.patient_age}세` : ""}`;

  /* 학부 카드 — 콤팩트 가로형 */
  const routeCards = (data.department_cards || []).map(card => `
    <div class="col-auto">
      <div class="dept-chip ${departmentChipClass(card.department_major)}">
        <i class="bi ${departmentIcon(card.department_major)} dept-chip-icon"></i>
        <span class="dept-chip-name">${escapeHtml(card.department_major)}</span>
        <span class="dept-chip-count">${card.count}</span>
      </div>
    </div>`).join("");

  /* 검사항목 테이블 — 가독성 강화 */
  const testRows = (data.tests || []).map(test => `
    <tr>
      <td class="text-center">
        ${test.test_code
          ? `<code class="test-code-badge">${escapeHtml(test.test_code)}</code>`
          : `<span class="text-secondary">-</span>`}
      </td>
      <td class="test-name-cell">${escapeHtml(test.test_name)}</td>
      <td><span class="department-badge ${departmentClass(test.department_major)}">${escapeHtml(test.department_major)}</span></td>
      <td class="text-center">${test.aliquot_required  ? '<span class="work-tag work-tag-aliquot"><i class="bi bi-scissors"></i>분주</span>'  : ""}</td>
      <td class="text-center">${test.transfer_required ? '<span class="work-tag work-tag-transfer"><i class="bi bi-arrow-right-circle"></i>전달</span>' : ""}</td>
    </tr>`).join("");

  /* 도착 확인 정보 */
  const arrivalInfo = data.arrival_checked_at ? `
    <div class="arrival-info-row mb-3">
      <div class="arrival-info-item"><span>확인자</span><strong>${escapeHtml(data.arrival_checked_by || "-")}</strong></div>
      <div class="arrival-info-item"><span>확인시간</span><strong>${formatDate(data.arrival_checked_at)}</strong></div>
      <div class="arrival-info-item"><span>확인 PC</span><strong>${escapeHtml(data.arrival_workstation || "-")}</strong></div>
    </div>` : "";

  /* 상태 뱃지 라인 */
  const badges = [
    `<span class="result-badge ${statusOk ? "badge-ok" : "badge-warn"}">
       <i class="bi bi-${statusOk ? "check-circle-fill" : "question-circle-fill"}"></i>
       ${statusOk ? "접수 확인" : "접수 없음"}
     </span>`,
    `<span class="result-badge ${data.arrived ? "badge-ok" : "badge-neutral"}">
       <i class="bi bi-${data.arrived ? "check2-all" : "eye"}"></i>
       ${data.arrived ? "도착처리" : "조회"}
     </span>`,
    data.aliquot_required  ? `<span class="result-badge badge-danger"><i class="bi bi-scissors"></i>분주 필요</span>` : "",
    data.transfer_required ? `<span class="result-badge badge-warn"><i class="bi bi-arrow-right-circle"></i>전달 필요</span>` : "",
  ].join("");

  document.getElementById("scanResult").innerHTML = `
    <div class="page-panel scan-result-panel">

      <!-- 접수번호 + 상태 뱃지 -->
      <div class="scan-result-header">
        <div>
          <div class="scan-result-label">접수번호</div>
          <div class="scan-result-accession">${escapeHtml(data.accession_no)}</div>
        </div>
        <div class="badge-row">${badges}</div>
      </div>

      <!-- 환자·검체·상태 정보 (콤팩트 3칸) -->
      <div class="patient-info-row mb-3">
        <div class="patient-info-item">
          <span>환자명 / 나이</span>
          <strong>${escapeHtml(patientText)}</strong>
        </div>
        <div class="patient-info-item">
          <span>검체명</span>
          <strong>${escapeHtml(data.specimen_name || "-")}</strong>
        </div>
        <div class="patient-info-item">
          <span>처리 상태</span>
          <strong>${escapeHtml(data.message)}</strong>
        </div>
      </div>

      <!-- 도착 확인 정보 -->
      ${arrivalInfo}

      <!-- 학부 칩 (가로 나열) -->
      <div class="row g-2 mb-4 dept-chips-row">
        ${routeCards || '<div class="col-12"><div class="alert alert-warning py-2 mb-0">표시할 검사항목이 없습니다.</div></div>'}
      </div>

      <!-- 검사항목 테이블 -->
      <div class="table-responsive">
        <table class="table table-hover align-middle test-result-table mb-0">
          <thead>
            <tr>
              <th style="width:100px">검사코드</th>
              <th>검사항목</th>
              <th style="width:120px">학부</th>
              <th class="text-center" style="width:72px">분주</th>
              <th class="text-center" style="width:72px">전달</th>
            </tr>
          </thead>
          <tbody>
            ${testRows || '<tr><td colspan="5" class="text-center text-secondary py-3">검사항목이 없습니다.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>`;
}
