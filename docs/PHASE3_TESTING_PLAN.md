# Phase 3: Selenium and JMeter Testing Plan

This phase performs black-box functional and performance testing for the
Online-Boutique microservice system.

## Environment

- Target frontend URL: `http://127.0.0.1:8088`
- Selenium test runner: Python Selenium with pytest
- Browser: Microsoft Edge by default
- JMeter: Apache JMeter 5.1.1
- Java: JDK 1.8

## Selenium Functional Tests

The Selenium tests are stored in:

```text
FinalProject/tests/selenium/
```

Test cases:

1. Home page loads and lists product links.
2. Product detail page for `OLJCESPC7Z` renders `Sunglasses`.
3. User can add `Sunglasses` to cart with quantity `2`.
4. User can checkout and see order completion information.

Run:

```powershell
.\FinalProject\scripts\run-phase3-selenium.ps1
```

Screenshots are saved in:

```text
FinalProject/data/phase3/selenium/screenshots/
```

Page-load and interaction-response timing metrics are saved in:

```text
FinalProject/data/phase3/selenium/timing_metrics.csv
```

## JMeter Performance Tests

The JMeter test plan is stored in:

```text
FinalProject/tests/jmeter/online_boutique_load_test.jmx
```

The test plan simulates the shopping flow:

1. Open home page.
2. Open product detail page.
3. Add product to cart.
4. View cart.
5. Checkout.

Recommended runs:

```powershell
.\FinalProject\scripts\run-phase3-jmeter.ps1 -Threads 1 -Loops 1 -RunName smoke-001
.\FinalProject\scripts\run-phase3-jmeter.ps1 -Threads 10 -RampUp 20 -Loops 5 -RunName normal-001
.\FinalProject\scripts\run-phase3-jmeter.ps1 -Threads 20 -RampUp 30 -Loops 5 -RunName higher-001
```

Outputs are saved in:

```text
FinalProject/data/phase3/jmeter/<run-name>/
```

## Report Evidence

Keep only essential screenshots:

- Selenium pytest pass result.
- Selenium order complete page.
- Selenium timing metrics CSV.
- JMeter Aggregate Report or HTML Dashboard statistics.
- Optional Grafana dashboard during JMeter load.

## Relation To KPIRoot

Phase 3 validates functional correctness and load performance. It is not the
main source of KPIRoot fault data. KPIRoot should primarily use Phase 2 fault
datasets, while Phase 3 load data can be used as supplementary normal/high-load
context if needed.
