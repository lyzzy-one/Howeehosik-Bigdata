'use client';

import { useState, useEffect, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Header from '@/components/Header';
import BottomNav from '@/components/BottomNav';
import RadarChart from '@/components/RadarChart';

declare global {
  interface Window {
    kakao: any;
  }
}

const API_BASE_URL = 'http://localhost:8000';

// 등급 계산
function getGrade(score: number): { grade: string; color: string } {
  if (score >= 90) return { grade: 'A', color: 'text-green-600' };
  if (score >= 80) return { grade: 'B', color: 'text-blue-600' };
  if (score >= 70) return { grade: 'C', color: 'text-yellow-600' };
  if (score >= 60) return { grade: 'D', color: 'text-orange-600' };
  return { grade: 'F', color: 'text-red-600' };
}

// 카테고리 정보
const categoryInfo: Record<string, { name: string; icon: string; description: string }> = {
  surveillance: { name: '감시 인프라', icon: '📹', description: 'CCTV, 방범카메라 등' },
  lighting: { name: '야간 조명', icon: '💡', description: '가로등, 보안등 등' },
  emergency: { name: '긴급 대응', icon: '🚨', description: '비상벨, 경찰서, 파출소 등' },
  safe_policy: { name: '안심정책', icon: '🛡️', description: '안심귀갓길 시설물' },
  route_access: { name: '귀가 접근성', icon: '🚶', description: '안심귀갓길 경로' },
};

const KAKAO_API_KEY = 'ccef25915035bf3d514e9fdfb756fc26';

function ResultContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const mapRef = useRef<any>(null);

  const lat = searchParams.get('lat');
  const lng = searchParams.get('lng');
  const address = searchParams.get('address');

  // 실제 API 호출
  useEffect(() => {
    const fetchAnalysis = async () => {
      if (!lat || !lng) {
        setError('위치 정보가 없습니다.');
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/analyze-coord`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            lat: parseFloat(lat),
            lon: parseFloat(lng),
            priority: 'balanced',
          }),
        });

        if (!response.ok) {
          throw new Error(`API 오류: ${response.status}`);
        }

        const data = await response.json();
        setResult(data);
      } catch (err) {
        console.error('API 호출 실패:', err);
        setError('분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalysis();
  }, [lat, lng]);

  // 카카오맵 스크립트 로드 및 지도 초기화
  useEffect(() => {
    if (loading || !result || !lat || !lng) return;

    const initMap = () => {
      const container = document.getElementById('result-map');
      if (!container || !window.kakao?.maps) return;

      const coords = new window.kakao.maps.LatLng(parseFloat(lat), parseFloat(lng));
      const options = {
        center: coords,
        level: 4,
      };
      mapRef.current = new window.kakao.maps.Map(container, options);

      // 내 위치 마커
      new window.kakao.maps.Marker({
        position: coords,
        map: mapRef.current,
      });
    };

    // 카카오맵 SDK 로드
    if (window.kakao && window.kakao.maps) {
      window.kakao.maps.load(initMap);
    } else {
      const script = document.createElement('script');
      script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_API_KEY}&libraries=services&autoload=false`;
      script.async = true;
      script.onload = () => {
        window.kakao.maps.load(initMap);
      };
      document.head.appendChild(script);
    }
  }, [loading, result, lat, lng]);

  // 저장하기
  const handleSave = () => {
    const history = JSON.parse(localStorage.getItem('search_history') || '[]');
    const newEntry = {
      id: Date.now(),
      address,
      lat,
      lng,
      score: result.total_score,
      grade: getGrade(result.total_score).grade,
      date: new Date().toISOString(),
    };
    history.unshift(newEntry);
    const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
    const filteredHistory = history.filter((item: any) => new Date(item.date).getTime() > thirtyDaysAgo);
    localStorage.setItem('search_history', JSON.stringify(filteredHistory.slice(0, 100)));
    alert('저장되었습니다!');
  };

  // 비교하기
  const handleCompare = () => {
    const compareList = JSON.parse(localStorage.getItem('compare_list') || '[]');
    if (compareList.length >= 3) {
      alert('최대 3개까지 비교할 수 있습니다.');
      return;
    }
    compareList.push({
      address,
      lat,
      lng,
      score: result.total_score,
      scores: result.category_scores,
    });
    localStorage.setItem('compare_list', JSON.stringify(compareList));
    router.push('/compare');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">안전도를 분석하고 있어요...</p>
          <p className="text-gray-400 text-sm mt-2">AI가 주변 시설을 분석 중입니다</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center p-6">
          <div className="text-4xl mb-4">😢</div>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => router.back()}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg"
          >
            돌아가기
          </button>
        </div>
      </div>
    );
  }

  const { grade, color } = getGrade(result.total_score);

  // 활성 카테고리만 필터링
  const activeCategories = Object.entries(result.category_scores).filter(
    ([_, value]: [string, any]) => value.active !== false
  );

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <Header title={address?.split(' ').slice(-2).join(' ') || '분석 결과'} showBack />

      <div className="max-w-lg mx-auto">
        {/* 종합 점수 */}
        <div className="bg-white p-6 border-b border-gray-200">
          <div className="text-center">
            <div className="text-sm text-gray-500 mb-2">종합 안전도</div>
            <div className="flex items-center justify-center gap-4">
              <span className="text-5xl font-bold text-gray-900">{result.total_score}</span>
              <span className={`text-4xl font-bold ${color}`}>{grade}</span>
            </div>
            <p className="text-gray-500 text-sm mt-2">{result.grade}</p>
          </div>
        </div>

        {/* 한 줄 요약 */}
        {result.one_line_summary && (
          <div className="bg-indigo-50 p-4 border-b border-indigo-100">
            <p className="text-indigo-800 text-sm">{result.one_line_summary}</p>
          </div>
        )}

        {/* 레이더 차트 */}
        <div className="bg-white p-6 border-b border-gray-200">
          <RadarChart
            scores={{
              surveillance: result.category_scores.surveillance?.score || 0,
              lighting: result.category_scores.lighting?.score || 0,
              emergency: result.category_scores.emergency?.score || 0,
              safe_policy: result.category_scores.safe_policy?.score || 0,
              route_access: result.category_scores.route_access?.score || 0,
            }}
          />
        </div>

        {/* 카테고리별 상세 */}
        <div className="bg-white border-b border-gray-200">
          {activeCategories.map(([key, value]: [string, any]) => (
            <div key={key} className="border-b border-gray-100 last:border-0">
              <button
                onClick={() => setExpandedCategory(expandedCategory === key ? null : key)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{categoryInfo[key]?.icon}</span>
                  <span className="font-medium text-gray-900">{value.name || categoryInfo[key]?.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`font-bold ${getGrade(value.score).color}`}>
                    {value.score}점
                  </span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className={`w-5 h-5 text-gray-400 transition-transform ${expandedCategory === key ? 'rotate-180' : ''}`}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                  </svg>
                </div>
              </button>
              {expandedCategory === key && value.evidence && (
                <div className="px-6 pb-4 text-sm text-gray-600 bg-gray-50">
                  <p className="mb-2">{categoryInfo[key]?.description}</p>
                  <ul className="space-y-1">
                    {Object.entries(value.evidence).map(([evidenceKey, evidenceValue]: [string, any]) => (
                      <li key={evidenceKey}>
                        • {evidenceKey.replace(/_/g, ' ')}: {evidenceValue !== null ? evidenceValue : '데이터 없음'}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 지도 */}
        <div className="bg-white p-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-3">분석 위치</h3>
          <div id="result-map" className="w-full h-48 rounded-xl overflow-hidden bg-gray-100" />
        </div>

        {/* AI 리포트 */}
        <div className="bg-white p-6 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            AI 분석 리포트
            {result.report_source && (
              <span className="text-xs bg-indigo-100 text-indigo-600 px-2 py-0.5 rounded">
                {result.report_source}
              </span>
            )}
          </h3>
          <div className="text-gray-700 text-sm leading-relaxed whitespace-pre-line">
            {result.ai_report}
          </div>
        </div>

        {/* 권장 행동 */}
        {result.recommended_action && (
          <div className="bg-amber-50 p-4 border-b border-amber-100">
            <h4 className="font-medium text-amber-800 mb-1">권장 행동</h4>
            <p className="text-amber-700 text-sm">{result.recommended_action}</p>
          </div>
        )}

        {/* 액션 버튼 */}
        <div className="p-4 flex gap-3">
          <button
            onClick={handleCompare}
            className="flex-1 py-3 border border-indigo-600 text-indigo-600 font-semibold rounded-xl hover:bg-indigo-50 transition-colors"
          >
            비교하기
          </button>
          <button
            onClick={handleSave}
            className="flex-1 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition-colors"
          >
            저장하기
          </button>
        </div>

        {/* 면책 조항 */}
        {result.disclaimer && (
          <div className="px-4 pb-4">
            <p className="text-xs text-gray-400 text-center">{result.disclaimer}</p>
          </div>
        )}
      </div>

      <BottomNav />
    </div>
  );
}

export default function ResultPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <ResultContent />
    </Suspense>
  );
}
