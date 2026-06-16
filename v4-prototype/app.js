const stageLinks = document.querySelectorAll(".stage-link");
const taskForm = document.querySelector("#taskForm");
const taskInput = document.querySelector("#taskInput");
const traceItems = [...document.querySelectorAll("#traceList li")];
const traceStatus = document.querySelector("#traceStatus");
const currentTask = document.querySelector("#currentTask");
const materialOutput = document.querySelector("#materialOutput");

const materialMap = {
  outline: {
    title: "《企业拜访提纲》",
    lines: [
      "1. 确认 AI 推理芯片产品量产进度与核心客户。",
      "2. 介绍园区高企免租、AI 产业扶持与算力资源。",
      "3. 明确研发办公、洁净改造和人才政策需求。",
    ],
  },
  wechat: {
    title: "《微信跟进话术》",
    lines: [
      "张总您好，基于贵司 AI 推理芯片方向，我们初步判断与园区半导体链条补强方向高度契合。",
      "园区可重点支持高企免租、AI 产业扶持与算力资源对接。",
      "方便今天下午安排 20 分钟，我们把政策和空间方案向您做一个简要说明。",
    ],
  },
  report: {
    title: "《领导汇报摘要》",
    lines: [
      "未来芯片科技建议列为本周重点推进对象。",
      "核心依据：补链价值明确、政策抓手清晰、历史跟进意愿较高。",
      "下一步建议：安排技术负责人拜访，同步准备政策包与空间方案。",
    ],
  },
  risk: {
    title: "《风险复核清单》",
    lines: [
      "1. 核实量产交付能力和核心客户真实性。",
      "2. 补充融资资金用途与现金流情况。",
      "3. 确认知识产权、诉讼和合规记录。",
    ],
  },
};

function activateNav(targetId) {
  stageLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.target === targetId);
  });
}

stageLinks.forEach((link) => {
  link.addEventListener("click", () => {
    const target = document.querySelector(`#${link.dataset.target}`);
    activateNav(link.dataset.target);
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    taskInput.value = button.dataset.prompt;
    taskInput.focus();
  });
});

function runTrace() {
  traceItems.forEach((item) => item.classList.remove("done", "active"));
  traceStatus.textContent = "执行中";

  traceItems.forEach((item, index) => {
    window.setTimeout(() => {
      traceItems.forEach((row, rowIndex) => {
        row.classList.toggle("done", rowIndex < index);
        row.classList.toggle("active", rowIndex === index);
      });

      if (index === traceItems.length - 1) {
        window.setTimeout(() => {
          traceItems.forEach((row) => row.classList.add("done"));
          traceItems.forEach((row) => row.classList.remove("active"));
          traceStatus.textContent = "已生成";
          document.querySelector("#brief")?.scrollIntoView({ behavior: "smooth" });
          activateNav("brief");
        }, 650);
      }
    }, index * 620);
  });
}

taskForm.addEventListener("submit", (event) => {
  event.preventDefault();
  currentTask.textContent = taskInput.value.includes("未来芯片")
    ? "未来芯片科技招商研判 + 拜访材料生成"
    : "招商任务研判 + 行动材料生成";
  document.querySelector("#trace")?.scrollIntoView({ behavior: "smooth" });
  activateNav("trace");
  runTrace();
});

document.querySelectorAll("[data-material]").forEach((button) => {
  button.addEventListener("click", () => {
    const material = materialMap[button.dataset.material];
    materialOutput.innerHTML = `
      <h4>${material.title}</h4>
      ${material.lines.map((line) => `<p>${line}</p>`).join("")}
    `;
  });
});

const observer = new IntersectionObserver(
  (entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (visible) activateNav(visible.target.id);
  },
  { threshold: [0.35, 0.6] }
);

["desk", "trace", "brief", "action", "value"].forEach((id) => {
  const section = document.querySelector(`#${id}`);
  if (section) observer.observe(section);
});
