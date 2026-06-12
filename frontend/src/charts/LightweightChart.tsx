import { useEffect, useRef } from "react";
import { createChart, AreaSeries, type IChartApi, ColorType } from "lightweight-charts";

interface ChartDataPoint {
  time: string;
  value: number;
}

interface Props {
  data: ChartDataPoint[];
  height?: number;
  lineColor?: string;
  areaTopColor?: string;
  areaBottomColor?: string;
  disableScroll?: boolean;
}

export default function LightweightChart({
  data,
  height = 400,
  lineColor = "#00d4aa",
  areaTopColor = "rgba(0, 212, 170, 0.3)",
  areaBottomColor = "rgba(0, 212, 170, 0.0)",
  disableScroll = false,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8888a0",
        fontFamily: "'Inter', sans-serif",
      },
      grid: {
        vertLines: { color: "rgba(42, 42, 62, 0.5)" },
        horzLines: { color: "rgba(42, 42, 62, 0.5)" },
      },
      crosshair: {
        vertLine: { color: "#4d8eff", width: 1, style: 2 },
        horzLine: { color: "#4d8eff", width: 1, style: 2 },
      },
      timeScale: {
        borderColor: "#2a2a3e",
        timeVisible: false,
      },
      rightPriceScale: {
        borderColor: "#2a2a3e",
      },
      ...(disableScroll && {
        handleScroll: { mouseWheel: false },
        handleScale: { mouseWheel: false },
      }),
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor,
      topColor: areaTopColor,
      bottomColor: areaBottomColor,
      lineWidth: 2,
      priceFormat: {
        type: "custom",
        formatter: (price: number) =>
          "$" + price.toLocaleString("en-US", { maximumFractionDigits: 0 }),
      },
    });

    if (data.length > 0) {
      series.setData(data);
      chart.timeScale().fitContent();
    }

    chartRef.current = chart;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        chart.applyOptions({ width: entry.contentRect.width });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data, height, lineColor, areaTopColor, areaBottomColor, disableScroll]);

  return <div ref={containerRef} />;
}
