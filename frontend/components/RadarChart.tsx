'use client';

import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import { Radar } from 'react-chartjs-2';

ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

interface RadarChartProps {
  scores: {
    surveillance: number;
    lighting: number;
    emergency: number;
    safe_policy: number;
    route_access: number;
  };
  label?: string;
  color?: string;
  showLegend?: boolean;
}

const categoryLabels: Record<string, string> = {
  surveillance: '감시 인프라',
  lighting: '야간 조명',
  emergency: '긴급 대응',
  safe_policy: '안심정책',
  route_access: '귀가 접근성',
};

export default function RadarChart({
  scores,
  label = '안전 점수',
  color = 'rgba(99, 102, 241, 0.7)',
  showLegend = false
}: RadarChartProps) {
  const data = {
    labels: Object.keys(scores).map(key => categoryLabels[key] || key),
    datasets: [
      {
        label,
        data: Object.values(scores),
        backgroundColor: color.replace('0.7', '0.2'),
        borderColor: color,
        borderWidth: 2,
        pointBackgroundColor: color,
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: color,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: true,
    scales: {
      r: {
        angleLines: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
        pointLabels: {
          font: {
            size: 12,
          },
          color: '#374151',
        },
        suggestedMin: 0,
        suggestedMax: 100,
        ticks: {
          stepSize: 20,
          font: {
            size: 10,
          },
          color: '#9ca3af',
        },
      },
    },
    plugins: {
      legend: {
        display: showLegend,
      },
    },
  };

  return (
    <div className="w-full max-w-xs mx-auto">
      <Radar data={data} options={options} />
    </div>
  );
}
