from __future__ import annotations

import argparse
import csv
import html
from datetime import date
from pathlib import Path
from typing import Iterable

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    LongTable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent


class ReportDocTemplate(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name == "Heading1":
                self.notify("TOCEntry", (0, flowable.getPlainText(), self.page))
            elif style_name == "Heading2":
                self.notify("TOCEntry", (1, flowable.getPlainText(), self.page))


def pick_font(candidates: Iterable[Path]) -> Path:
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("No usable Chinese font found.")


def register_fonts() -> dict[str, str]:
    font_dir = Path(r"C:\Windows\Fonts")
    regular = pick_font(
        [
            font_dir / "NotoSansSC-VF.ttf",
            font_dir / "Deng.ttf",
            font_dir / "simfang.ttf",
            font_dir / "simkai.ttf",
        ]
    )
    bold = pick_font(
        [
            font_dir / "simhei.ttf",
            font_dir / "NotoSansSC-VF.ttf",
            font_dir / "Dengb.ttf",
        ]
    )
    serif = pick_font(
        [
            font_dir / "NotoSerifSC-VF.ttf",
            font_dir / "simsunb.ttf",
            font_dir / "Deng.ttf",
        ]
    )

    pdfmetrics.registerFont(TTFont("ReportSong", str(regular)))
    pdfmetrics.registerFont(TTFont("ReportHei", str(bold)))
    pdfmetrics.registerFont(TTFont("ReportSerif", str(serif)))
    return {"regular": "ReportSong", "bold": "ReportHei", "serif": "ReportSerif"}


def build_styles(fonts: dict[str, str]) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {}

    styles["Title"] = ParagraphStyle(
        "Title",
        parent=base["Title"],
        fontName=fonts["bold"],
        fontSize=24,
        leading=32,
        alignment=TA_CENTER,
        spaceAfter=18,
        wordWrap="CJK",
    )
    styles["Subtitle"] = ParagraphStyle(
        "Subtitle",
        parent=base["Normal"],
        fontName=fonts["bold"],
        fontSize=15,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=12,
        wordWrap="CJK",
    )
    styles["CoverInfo"] = ParagraphStyle(
        "CoverInfo",
        parent=base["Normal"],
        fontName=fonts["regular"],
        fontSize=13,
        leading=23,
        alignment=TA_LEFT,
        wordWrap="CJK",
    )
    styles["Heading1"] = ParagraphStyle(
        "Heading1",
        parent=base["Heading1"],
        fontName=fonts["bold"],
        fontSize=17,
        leading=24,
        spaceBefore=14,
        spaceAfter=8,
        wordWrap="CJK",
    )
    styles["Heading2"] = ParagraphStyle(
        "Heading2",
        parent=base["Heading2"],
        fontName=fonts["bold"],
        fontSize=13,
        leading=20,
        spaceBefore=10,
        spaceAfter=6,
        wordWrap="CJK",
    )
    styles["Body"] = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        fontName=fonts["regular"],
        fontSize=10.5,
        leading=17,
        firstLineIndent=21,
        alignment=TA_JUSTIFY,
        spaceAfter=5,
        wordWrap="CJK",
    )
    styles["BodyNoIndent"] = ParagraphStyle(
        "BodyNoIndent",
        parent=styles["Body"],
        firstLineIndent=0,
    )
    styles["Bullet"] = ParagraphStyle(
        "Bullet",
        parent=styles["BodyNoIndent"],
        leftIndent=16,
        firstLineIndent=-12,
        bulletIndent=0,
    )
    styles["Caption"] = ParagraphStyle(
        "Caption",
        parent=base["Normal"],
        fontName=fonts["regular"],
        fontSize=9,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#3f3f46"),
        spaceBefore=3,
        spaceAfter=8,
        wordWrap="CJK",
    )
    styles["TableCell"] = ParagraphStyle(
        "TableCell",
        parent=base["Normal"],
        fontName=fonts["regular"],
        fontSize=8.5,
        leading=12,
        wordWrap="CJK",
    )
    styles["TableHeader"] = ParagraphStyle(
        "TableHeader",
        parent=styles["TableCell"],
        fontName=fonts["bold"],
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    styles["Code"] = ParagraphStyle(
        "Code",
        parent=base["Code"],
        fontName=fonts["regular"],
        fontSize=8.2,
        leading=11,
        textColor=colors.HexColor("#27272a"),
        leftIndent=6,
        rightIndent=6,
        wordWrap="LTR",
    )
    styles["TOCHeading"] = ParagraphStyle(
        "TOCHeading",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
    )
    return styles


def esc(text: object) -> str:
    return html.escape(str(text), quote=False)


def p(text: str, styles: dict[str, ParagraphStyle], style: str = "Body") -> Paragraph:
    return Paragraph(esc(text), styles[style])


def raw_p(text: str, styles: dict[str, ParagraphStyle], style: str = "Body") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return raw_p(f"• {esc(text)}", styles, "Bullet")


def code(text: str, styles: dict[str, ParagraphStyle]) -> Preformatted:
    return Preformatted(text, styles["Code"], maxLineLength=88)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def table(
    rows: list[list[object]],
    styles: dict[str, ParagraphStyle],
    widths: list[float] | None = None,
    font_size: float = 8.5,
) -> LongTable:
    if not rows:
        return LongTable([[""]])

    header = [Paragraph(esc(cell), styles["TableHeader"]) for cell in rows[0]]
    body = []
    cell_style = styles["TableCell"]
    if font_size != 8.5:
        cell_style = ParagraphStyle("TableCellSmall", parent=styles["TableCell"], fontSize=font_size, leading=font_size + 3)
    for row in rows[1:]:
        body.append([Paragraph(esc(cell), cell_style) for cell in row])
    data = [header] + body

    tbl = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9ca3af")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    return tbl


def image_flowable(
    relative_path: str,
    caption: str,
    styles: dict[str, ParagraphStyle],
    max_width: float = 15.4 * cm,
    max_height: float = 8.4 * cm,
) -> list:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        return [p(f"图片缺失：{relative_path}", styles, "BodyNoIndent")]
    with PILImage.open(path) as img:
        width, height = img.size
    scale = min(max_width / width, max_height / height, 1.0)
    flowables = [
        Image(str(path), width=width * scale, height=height * scale, hAlign="CENTER"),
        raw_p(f"<b>{esc(caption)}</b>", styles, "Caption"),
    ]
    return flowables


def cover_table(styles: dict[str, ParagraphStyle]) -> Table:
    rows = [
        ["实验标题：", "Online-Boutique 运维实验与 ISSRE24-KPIRoot 论文复现"],
        ["课程名称：", "软件测试与维护"],
        ["报告范围：", "组内两篇论文复现任务中的一篇：ISSRE24-KPIRoot"],
        ["微服务系统：", "JoinFyc/Online-Boutique"],
        ["参与者：", "王新杰（学号：2311901）；王子祺（学号：2312385）"],
        ["GitHub：", "https://github.com/Sinclair987/software-testing-final-project"],
        ["指导教师：", "张圣林"],
        ["完成日期：", str(date.today())],
    ]
    data = []
    for key, value in rows:
        value_text = esc(value)
        if key == "GitHub：":
            value_text = "https://github.com/Sinclair987/<br/>software-testing-final-project"
        data.append(
            [
                Paragraph(f"<b>{esc(key)}</b>", styles["CoverInfo"]),
                Paragraph(value_text, styles["CoverInfo"]),
            ]
        )
    tbl = Table(data, colWidths=[3.2 * cm, 12.4 * cm], hAlign="CENTER")
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return tbl


def draw_later_page(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d4d4d8"))
    canvas.line(doc.leftMargin, A4[1] - 1.45 * cm, A4[0] - doc.rightMargin, A4[1] - 1.45 * cm)
    canvas.setFillColor(colors.HexColor("#52525b"))
    canvas.setFont("ReportSong", 8.5)
    canvas.drawString(doc.leftMargin, A4[1] - 1.15 * cm, "软件测试与维护大作业报告")
    canvas.drawRightString(A4[0] - doc.rightMargin, A4[1] - 1.15 * cm, "ISSRE24-KPIRoot 复现")
    canvas.setStrokeColor(colors.HexColor("#d4d4d8"))
    canvas.line(doc.leftMargin, 1.35 * cm, A4[0] - doc.rightMargin, 1.35 * cm)
    canvas.drawCentredString(A4[0] / 2, 0.9 * cm, str(canvas.getPageNumber()))
    canvas.restoreState()


def draw_first_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#52525b"))
    canvas.setFont("ReportSong", 9)
    canvas.drawCentredString(A4[0] / 2, 0.9 * cm, "软件测试与维护（2026年春）课程大作业")
    canvas.restoreState()


def add_section(story: list, title: str, styles: dict[str, ParagraphStyle], level: int = 1) -> None:
    story.append(Paragraph(esc(title), styles["Heading1" if level == 1 else "Heading2"]))


def build_story(styles: dict[str, ParagraphStyle]) -> list:
    story: list = []

    logo = WORKSPACE_ROOT / "labs" / "实验报告模板" / "nankai.jpg"
    if logo.exists():
        with PILImage.open(logo) as img:
            w, h = img.size
        scale = min((15.2 * cm) / w, (3.2 * cm) / h)
        story.append(Image(str(logo), width=w * scale, height=h * scale, hAlign="CENTER"))
        story.append(Spacer(1, 1.2 * cm))

    story.extend(
        [
            raw_p("《软件测试与维护》大作业报告", styles, "Title"),
            raw_p("Online-Boutique 运维实验与 ISSRE24-KPIRoot 论文复现", styles, "Subtitle"),
            Spacer(1, 1.6 * cm),
            cover_table(styles),
            Spacer(1, 1.4 * cm),
            p("说明：课程大作业以小组形式完成，基本要求包含两篇论文复现。本报告仅记录组内其中一篇论文 ISSRE24-KPIRoot 的复现工作；另一篇论文复现与智能体封装由组内其他成员另行整合。", styles, "BodyNoIndent"),
            PageBreak(),
        ]
    )

    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOCLevel1",
            fontName="ReportSong",
            fontSize=10.5,
            leading=17,
            leftIndent=0,
            firstLineIndent=0,
            spaceBefore=4,
        ),
        ParagraphStyle(
            "TOCLevel2",
            fontName="ReportSong",
            fontSize=9.5,
            leading=15,
            leftIndent=16,
            firstLineIndent=0,
            spaceBefore=2,
        ),
    ]
    story.append(raw_p("目录", styles, "TOCHeading"))
    story.append(toc)
    story.append(PageBreak())

    story.append(raw_p("摘要", styles, "Heading1"))
    story.append(
        p(
            "本报告围绕 JoinFyc/Online-Boutique 开源微服务系统，记录本地部署、监控维护、故障注入、黑盒测试以及 ISSRE 2024 论文 KPIRoot 的复现工作。实验使用 Minikube 部署 Online-Boutique，使用 Prometheus、Grafana、Blackbox Exporter 与 ChaosMesh 采集正常与故障状态下的时序 KPI 数据，使用 Selenium 和 JMeter 验证系统功能与性能，最后基于采集数据实现 KPIRoot 中的 PAA、SAX、相似度分析、Granger 风格因果得分和综合排序。实验结果显示，在 paymentservice CPU Stress、frontend CPU Stress 和 paymentservice Pod Kill 三组故障数据中，复现算法均能将真实根因服务排在第一位。",
            styles,
        )
    )
    story.append(
        p(
            "关键词：Online-Boutique；Prometheus；Grafana；ChaosMesh；Selenium；JMeter；KPIRoot；根因定位",
            styles,
            "BodyNoIndent",
        )
    )

    add_section(story, "1 作业范围与系统概况", styles)
    story.append(
        p(
            "课程要求围绕微服务系统完成部署、测试、维护和论文复现，并在报告中展示微服务系统、Selenium/JMeter 测试、ChaosMesh 故障注入、Prometheus/Grafana 监控、异常数据采集与论文算法效果。本项目选择第二档要求中的 Online-Boutique，而不是实验指南中的 SockShop，因此系统规模和服务组成更接近真实云原生应用。",
            styles,
        )
    )
    story.append(
        p(
            "需要特别说明的是，课程要求小组整体复现两篇异常检测或故障诊断相关论文。本报告对应组内其中一篇，即 ISSRE24-KPIRoot。报告中的代码、数据和结果均来自公开仓库：",
            styles,
        )
    )
    story.append(code("https://github.com/Sinclair987/software-testing-final-project", styles))
    story.append(
        table(
            [
                ["项目", "内容"],
                ["微服务系统", "JoinFyc/Online-Boutique"],
                ["本地集群", "Minikube"],
                ["命名空间", "online-boutique"],
                ["监控组件", "Prometheus、Grafana、Blackbox Exporter"],
                ["故障注入", "ChaosMesh"],
                ["测试工具", "Selenium、JMeter"],
                ["复现论文", "ISSRE 2024 - KPIRoot: Efficient Monitoring Metric-based Root Cause Localization in Large-scale Cloud Systems"],
            ],
            styles,
            widths=[3.5 * cm, 12.0 * cm],
        )
    )
    story.extend(image_flowable("data/phase3/selenium/screenshots/01_selenium_home_page.png", "图1 Online-Boutique 前端首页", styles))

    add_section(story, "2 阶段一：微服务系统部署", styles)
    story.append(
        p(
            "阶段一完成 Online-Boutique 在 Minikube 中的部署。部署时使用 release/kubernetes-manifests.yaml 中的预构建镜像，并创建 online-boutique 命名空间。部署完成后，12 个业务 Pod 均进入 1/1 Running 状态，frontend 服务通过本地端口转发暴露到 127.0.0.1:8088。",
            styles,
        )
    )
    story.append(code("kubectl apply -n online-boutique -f .\\FinalProject\\Online-Boutique\\release\\kubernetes-manifests.yaml\nkubectl wait --for=condition=available deployment --all -n online-boutique --timeout=300s\nkubectl port-forward -n online-boutique service/frontend 8088:80", styles))
    story.append(
        p(
            "直接访问 Minikube NodePort 在 Windows 环境下不够稳定，因此实验中采用 kubectl port-forward 作为稳定前端入口。项目保留 resume-online-boutique.ps1 和 port-forward-frontend.ps1 作为重启后恢复脚本。",
            styles,
        )
    )

    add_section(story, "3 阶段二：监控、故障注入与数据采集", styles)
    story.append(
        p(
            "阶段二复用 monitoring 命名空间中的 Prometheus 与 Grafana，并部署 Blackbox Exporter 对 Online-Boutique 前端进行探测。Prometheus 能采集容器 CPU、内存、文件系统读写、Pod 状态、容器重启次数以及前端 probe_success/probe_duration_seconds 等指标。Grafana Dashboard 用于观察故障前、故障中和恢复后的指标变化。",
            styles,
        )
    )
    story.append(
        table(
            [
                ["组件", "作用"],
                ["Prometheus", "采集 Kubernetes、cadvisor、kube-state-metrics、node-exporter 与 Blackbox 指标"],
                ["Grafana", "展示 Online-Boutique Dashboard，包括 CPU、内存、运行状态和探针指标"],
                ["Blackbox Exporter", "提供前端可用性和响应耗时指标，作为服务质量告警 KPI"],
                ["ChaosMesh", "注入 CPU Stress 和 Pod Kill 故障"],
            ],
            styles,
            widths=[3.5 * cm, 12.0 * cm],
        )
    )
    story.extend(image_flowable("data/phase2/stress-paymentservice-cpu-001/screenshots/04_grafana_baseline_dashboard_overview.png", "图2 Grafana 正常基线监控面板", styles))
    story.append(
        p(
            "阶段二最终保留三组故障数据。每组数据均包含 metadata.yaml、Prometheus 原始 query_range 导出、处理后的 kpi_matrix.csv、series_labels.json 和截图证据。",
            styles,
        )
    )
    story.append(
        table(
            [
                ["数据集", "故障类型", "目标服务", "矩阵规模", "阶段四真实根因"],
                ["stress-paymentservice-cpu-001", "CPU Stress", "paymentservice", "115 行 × 62 列", "cpu__paymentservice"],
                ["pod-kill-paymentservice-001", "Pod Kill", "paymentservice", "67 行 × 62 列", "paymentservice 服务"],
                ["stress-frontend-cpu-001", "CPU Stress", "frontend", "68 行 × 60 列", "cpu__frontend"],
            ],
            styles,
            widths=[4.7 * cm, 2.7 * cm, 2.6 * cm, 2.8 * cm, 3.0 * cm],
            font_size=8,
        )
    )
    story.extend(image_flowable("data/phase2/stress-paymentservice-cpu-001/screenshots/10_grafana_fault_paymentservice_cpu_spike.png", "图3 paymentservice CPU Stress 故障期间 CPU 指标升高", styles))
    story.extend(image_flowable("data/phase2/stress-frontend-cpu-001/screenshots/02_grafana_frontend_cpu_spike_overview.png", "图4 frontend CPU Stress 故障期间 CPU 指标升高", styles))
    story.append(
        p(
            "paymentservice CPU Stress 场景中，cpu__paymentservice 从约 0.00064 升至故障窗口平均约 0.16999；frontend CPU Stress 场景中，cpu__frontend 从约 0.016 升至故障窗口平均约 0.170，且前端探针耗时出现升高。Pod Kill 场景中 Kubernetes 快速创建替换 Pod，整体指标变化较弱，但原始 Prometheus 数据保留了旧 Pod 与新 Pod 的身份变化。",
            styles,
        )
    )

    add_section(story, "4 阶段三：Selenium 与 JMeter 测试", styles)
    story.append(
        p(
            "阶段三使用 Selenium 对 Online-Boutique 前端核心购物流程进行功能测试，使用 JMeter 对首页、商品详情、加入购物车、购物车和结算流程进行性能测试。Selenium 运行环境为 Microsoft Edge，JMeter 版本为 5.1.1。",
            styles,
        )
    )
    selenium_rows = [["测试用例", "指标", "类型", "时间 ms"]]
    for row in read_csv(PROJECT_ROOT / "data/phase3/selenium/timing_metrics.csv"):
        selenium_rows.append([row["test_case"], row["metric_name"], row["metric_type"], row["value_ms"]])
    story.append(table(selenium_rows, styles, widths=[4.7 * cm, 5.1 * cm, 2.4 * cm, 2.6 * cm], font_size=8))
    story.extend(image_flowable("data/phase3/selenium/screenshots/04_selenium_order_complete.png", "图5 Selenium 结算流程完成页面", styles))
    jmeter_rows = [["Run", "Main Samples", "Raw Samples", "Errors", "Error %", "Avg ms", "P90 ms", "P95 ms"]]
    for row in read_csv(PROJECT_ROOT / "data/phase3/jmeter/summary.csv"):
        jmeter_rows.append(
            [
                row["run"],
                row["main_samples"],
                row["raw_samples"],
                row["errors"],
                row["error_pct"],
                row["avg_ms"],
                row["p90_ms"],
                row["p95_ms"],
            ]
        )
    story.append(table(jmeter_rows, styles, widths=[2.4 * cm, 2.0 * cm, 2.0 * cm, 1.6 * cm, 1.6 * cm, 1.9 * cm, 1.8 * cm, 1.8 * cm], font_size=7.6))
    story.extend(image_flowable("data/phase3/jmeter/higher-001/screenshots/02_jmeter_higher_statistics_errors.png", "图6 JMeter higher-001 统计结果与错误率", styles))
    story.append(
        p(
            "Selenium 共 4 个用例全部通过，页面加载时间约 1.75 到 1.80 秒，关键交互响应时间低于 0.25 秒。JMeter 三组负载均未出现错误，higher-001 中 500 个主采样器的平均响应时间约 33.53 ms，P95 响应时间约 78 ms，说明在本地实验负载下系统保持稳定。",
            styles,
        )
    )

    add_section(story, "5 ISSRE24-KPIRoot 论文方法", styles)
    story.append(
        p(
            "KPIRoot 的目标是在系统级 alarm KPI 出现异常后，从大量底层 KPI 中定位最可能导致异常的根因 KPI。原论文面向 Cloud H 大规模云系统，输入包括主机集群层面的 alarm KPI 和 VM 级别的 CPU、内存、I/O、带宽等 KPI。其核心思想是：真正的根因 KPI 在异常窗口内应当与 alarm KPI 有相似的异常形状，并且其变化应当在时序上能够解释 alarm KPI 的变化。",
            styles,
        )
    )
    story.append(
        table(
            [
                ["原论文概念", "本项目映射"],
                ["Host/cluster alarm KPI", "synthetic_total_cpu、synthetic_total_memory、前端探针耗时与成功率"],
                ["VM KPI", "Online-Boutique 各服务的 CPU、内存、文件系统、运行状态等 KPI"],
                ["Root-cause VM", "被 ChaosMesh 注入故障的目标服务"],
            ],
            styles,
            widths=[5.0 * cm, 10.5 * cm],
        )
    )
    story.append(
        p(
            "复现实现包含以下步骤：读取阶段二 kpi_matrix.csv，构造系统级告警 KPI，缺失值处理与标准化，使用 PAA 降维，使用 SAX 将连续序列离散化为符号序列，根据故障注入元数据选择异常窗口，计算 SAX-Jaccard 相似度，计算 Granger 风格因果得分，最后按 0.9 × similarity + 0.1 × normalized_causality 生成综合得分并排序。",
            styles,
        )
    )
    story.append(code("src/kpiroot/algorithm.py\nsrc/kpiroot/data.py\nsrc/kpiroot/cli.py\ntests/kpiroot/test_algorithm.py", styles))

    add_section(story, "6 阶段四：KPIRoot 复现实验结果", styles)
    summary_rows = [["故障场景", "告警 KPI", "真实根因服务", "Top-1 KPI", "根因服务排名", "Hit@1", "Hit@3", "Hit@5"]]
    for row in read_csv(PROJECT_ROOT / "data/phase4/kpiroot/summary.csv"):
        summary_rows.append(
            [
                row["scenario_id"],
                row["alarm_column"],
                row["expected_service"],
                row["top1"],
                row["expected_service_rank"],
                row["hit_at_1"],
                row["hit_at_3"],
                row["hit_at_5"],
            ]
        )
    story.append(table(summary_rows, styles, widths=[3.7 * cm, 3.0 * cm, 2.3 * cm, 3.0 * cm, 1.6 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm], font_size=7.2))
    story.extend(image_flowable("data/phase4/kpiroot/stress-paymentservice-cpu-001/alarm_top_candidates.png", "图7 paymentservice CPU Stress：告警 KPI 与 Top 候选 KPI 对比", styles))
    story.extend(image_flowable("data/phase4/kpiroot/stress-paymentservice-cpu-001/topk_scores.png", "图8 paymentservice CPU Stress：Top-K 根因得分", styles))
    story.extend(image_flowable("data/phase4/kpiroot/stress-frontend-cpu-001/alarm_top_candidates.png", "图9 frontend CPU Stress：告警 KPI 与 Top 候选 KPI 对比", styles))
    story.extend(image_flowable("data/phase4/kpiroot/stress-frontend-cpu-001/topk_scores.png", "图10 frontend CPU Stress：Top-K 根因得分", styles))
    story.append(
        p(
            "三组故障中，综合 KPIRoot 排序均将真实根因服务排在第一位。其中两组 CPU Stress 的可解释性最强：系统级 synthetic_total_cpu 升高后，算法分别定位到 cpu__paymentservice 和 cpu__frontend。Pod Kill 场景中，服务级矩阵弱化了单个 Pod 身份变化，算法仍将 paymentservice 相关内存 KPI 排在第一，可作为边界案例。",
            styles,
        )
    )

    ablation_rows = [["故障场景", "方法", "Top-1 KPI", "根因服务排名", "Hit@1", "Hit@3", "Hit@5"]]
    for row in read_csv(PROJECT_ROOT / "data/phase4/kpiroot/ablation_summary.csv"):
        ablation_rows.append(
            [
                row["scenario_id"],
                row["method"],
                row["top1"],
                row["expected_service_rank"],
                row["hit_at_1"],
                row["hit_at_3"],
                row["hit_at_5"],
            ]
        )
    story.append(table(ablation_rows, styles, widths=[3.7 * cm, 2.6 * cm, 3.8 * cm, 1.8 * cm, 1.2 * cm, 1.2 * cm, 1.2 * cm], font_size=7.2))
    story.append(
        p(
            "消融实验显示，在本项目较短的课程实验时序数据上，单独使用 Granger 风格因果得分并不稳定；仅使用 SAX-Jaccard 相似度和使用 KPIRoot 综合得分均能稳定命中真实根因。该现象与原论文中“相似度和因果分析均有贡献”的结论并不矛盾，因为原论文使用的是更长、更复杂的工业数据，而本项目故障窗口较短、故障类型也更直接。",
            styles,
        )
    )

    add_section(story, "7 差异、局限与优化方向", styles)
    story.append(bullet("原论文使用 Cloud H 工业环境的大规模主机集群/VM KPI，本项目使用 Online-Boutique 微服务级 KPI，因此数据规模和实体层级不同。", styles))
    story.append(bullet("原论文的 alarm KPI 来自真实云系统告警，本项目使用聚合 CPU、聚合内存和前端探针指标模拟系统级告警。", styles))
    story.append(bullet("原论文自动检测异常段，本项目优先使用 ChaosMesh 故障注入时间窗口，自动趋势检测作为备用逻辑。", styles))
    story.append(bullet("Pod Kill 的 Pod 身份变化在服务级宽表中被部分合并，后续可以保留 Pod 级 KPI 或引入事件日志，以提升该类故障的可解释性。", styles))
    story.append(bullet("后续若扩展为完整小组报告，需要合并另一篇论文复现结果，并补充智能体封装部分的设计和效果。", styles))

    add_section(story, "8 参与者与贡献", styles)
    story.append(
        table(
            [
                ["参与者", "学号", "本报告对应工作"],
                ["王新杰", "2311901", "参与 ISSRE24-KPIRoot 阅读、环境部署、监控采集、故障数据整理、算法复现与报告整理。"],
                ["王子祺", "2312385", "参与 ISSRE24-KPIRoot 阅读、复现方案讨论、结果校核与报告整理。"],
            ],
            styles,
            widths=[3.0 * cm, 3.0 * cm, 9.5 * cm],
        )
    )

    add_section(story, "9 总结", styles)
    story.append(
        p(
            "本报告完成了 Online-Boutique 微服务系统部署、Prometheus/Grafana 监控、ChaosMesh 故障注入、Selenium/JMeter 测试以及 ISSRE24-KPIRoot 根因定位算法复现。实验结果表明，经过阶段二采集和处理的 KPI 数据能够支撑 KPIRoot 的核心流程，复现实现可以在三组故障场景中将真实根因服务排在第一位。与原论文相比，本项目的数据规模较小、场景经过课程实验简化，但已经覆盖了 PAA、SAX、相似度分析、因果得分、综合排序和消融实验等关键环节，能够作为组内一篇论文复现成果提交与展示。",
            styles,
        )
    )

    add_section(story, "参考资料", styles)
    refs = [
        "Wenwei Gu et al. KPIRoot: Efficient Monitoring Metric-based Root Cause Localization in Large-scale Cloud Systems. ISSRE 2024.",
        "JoinFyc/Online-Boutique: https://github.com/JoinFyc/Online-Boutique",
        "项目仓库：https://github.com/Sinclair987/software-testing-final-project",
        "软件测试与维护（2026年春）大作业要求。",
    ]
    for ref in refs:
        story.append(bullet(ref, styles))

    return story


def build_pdf(output: Path) -> None:
    fonts = register_fonts()
    styles = build_styles(fonts)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = ReportDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=2.0 * cm,
        leftMargin=2.0 * cm,
        topMargin=2.1 * cm,
        bottomMargin=1.8 * cm,
        title="软件测试与维护大作业报告",
        author="王新杰, 王子祺",
    )
    story = build_story(styles)
    doc.multiBuild(story, onFirstPage=draw_first_page, onLaterPages=draw_later_page)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the final Software Testing project PDF report.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "final_report" / "software_testing_final_report.pdf",
    )
    args = parser.parse_args()
    build_pdf(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
