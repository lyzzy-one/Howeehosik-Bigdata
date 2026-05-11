'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import BottomNav from '@/components/BottomNav';
import RadarChart from '@/components/RadarChart';

interface CompareItem {
  address: string;
  lat: string;
  lng: string;
  score: number;
  scores: {
    surveillance: { score: number };
    lighting: { score: number };
    emergency: { score: number };
    safe_policy: { score: number };
    route_access: { score: number };
  };
}

const categoryNames: Record<string, string> = {
  surveillance: '감시 인프라',
  lighting: '야간 조명',
  emergency: '긴급 대응',
  safe_policy: '안심정책',
  route_access: '귀가 접근성',
};

const colors = [
  'rgba(99, 102, 241, 0.7)',   // 인디고
  'rgba(239, 68, 68, 0.7)',    // 빨강
  'rgba(34, 197, 94, 0.7)',    // 초록
];

function getGrade(score: number): { grade: string; color: string } {
  if (score >= 90) return { grade: 'A', color: 'text-green-600 bg-green-100' };
  if (score >= 80) return { grade: 'B', color: 'text-blue-600 bg-blue-100' };
  if (score >= 70) return { grade: 'C', color: 'text-yellow-600 bg-yellow-100' };
  if (score >= 60) return { grade: 'D', color: 'text-orange-600 bg-orange-100' };
  return { grade: 'F', color: 'text-red-600 bg-red-100' };
}

export default function ComparePage() {
  const [compareList, setCompareList] = useState<CompareItem[]>([]);
  const router = useRouter();

  useEffect(() => {
    const saved = localStorage.getItem('compare_list');
    if (saved) {
      setCompareList(JSON.parse(saved));
    }
  }, []);

  const handleRemove = (index: number) => {
    const newList = compareList.filter((_, i) => i !== index);
    setCompareList(newList);
    localStorage.setItem('compare_list', JSON.stringify(newList));
  };

  const handleClearAll = () => {
    setCompareList([]);
    localStorage.removeItem('compare_list');
  };

  const handleAddMore = () => {
    router.push('/');
  };

  const handleSaveComparison = () => {
    if (compareList.length < 2) {
      alert('2개 이상의 주소를 비교해야 저장할 수 있습니다.');
      return;
    }
    const comparisons = JSON.parse(localStorage.getItem('saved_comparisons') || '[]');
    comparisons.unshift({
      id: Date.now(),
      items: compareList,
      date: new Date().toISOString(),
    });
    localStorage.setItem('saved_comparisons', JSON.stringify(comparisons.slice(0, 20)));
    alert('비교 결과가 저장되었습니다!');
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <Header title="주소 비교" showBack />

      <div className="max-w-lg mx-auto p-4">
        {/* 비교 목록 */}
        {compareList.length === 0 ? (
          <div className="bg-white rounded-xl p-8 text-center">
            <div className="text-4xl mb-4">📊</div>
            <h3 className="font-semibold text-gray-900 mb-2">비교할 주소가 없어요</h3>
            <p className="text-gray-500 text-sm mb-4">
              홈에서 주소를 검색하고<br />비교하기 버튼을 눌러주세요
            </p>
            <button
              onClick={handleAddMore}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              주소 검색하기
            </button>
          </div>
        ) : (
          <>
            {/* 주소 카드 */}
            <div className="flex gap-3 mb-6 overflow-x-auto pb-2">
              {compareList.map((item, index) => {
                const { grade, color } = getGrade(item.score);
                return (
                  <div
                    key={index}
                    className="flex-shrink-0 w-32 bg-white rounded-xl p-4 text-center relative"
                    style={{ borderTop: `4px solid ${colors[index].replace('0.7', '1')}` }}
                  >
                    <button
                      onClick={() => handleRemove(index)}
                      className="absolute top-2 right-2 w-5 h-5 bg-gray-200 rounded-full text-gray-500 text-xs hover:bg-gray-300"
                    >
                      ×
                    </button>
                    <div className="text-3xl font-bold text-gray-900">{item.score}</div>
                    <div className={`inline-block px-2 py-0.5 rounded text-sm font-medium ${color}`}>
                      {grade}
                    </div>
                    <div className="text-xs text-gray-500 mt-2 truncate">
                      {item.address.split(' ').slice(-2).join(' ')}
                    </div>
                  </div>
                );
              })}
              {compareList.length < 3 && (
                <button
                  onClick={handleAddMore}
                  className="flex-shrink-0 w-32 bg-gray-100 rounded-xl p-4 flex flex-col items-center justify-center hover:bg-gray-200 transition-colors border-2 border-dashed border-gray-300"
                >
                  <div className="text-2xl text-gray-400 mb-1">+</div>
                  <div className="text-sm text-gray-500">추가</div>
                </button>
              )}
            </div>

            {/* 레이더 차트 비교 */}
            {compareList.length >= 2 && (
              <div className="bg-white rounded-xl p-4 mb-4">
                <h3 className="font-semibold text-gray-900 mb-4">카테고리별 비교</h3>
                <div className="relative">
                  {compareList.map((item, index) => (
                    <div
                      key={index}
                      className="absolute inset-0"
                      style={{ opacity: index === 0 ? 1 : 0.7 }}
                    >
                      <RadarChart
                        scores={{
                          surveillance: item.scores.surveillance.score,
                          lighting: item.scores.lighting.score,
                          emergency: item.scores.emergency.score,
                          safe_policy: item.scores.safe_policy.score,
                          route_access: item.scores.route_access.score,
                        }}
                        label={item.address.split(' ').slice(-1)[0]}
                        color={colors[index]}
                      />
                    </div>
                  ))}
                  <RadarChart
                    scores={{
                      surveillance: compareList[0].scores.surveillance.score,
                      lighting: compareList[0].scores.lighting.score,
                      emergency: compareList[0].scores.emergency.score,
                      safe_policy: compareList[0].scores.safe_policy.score,
                      route_access: compareList[0].scores.route_access.score,
                    }}
                    label=""
                    color="transparent"
                  />
                </div>
                {/* 범례 */}
                <div className="flex justify-center gap-4 mt-4">
                  {compareList.map((item, index) => (
                    <div key={index} className="flex items-center gap-1 text-sm">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: colors[index].replace('0.7', '1') }}
                      />
                      <span className="text-gray-600">{item.address.split(' ').slice(-1)[0]}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 상세 비교 테이블 */}
            <div className="bg-white rounded-xl overflow-hidden mb-4">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">카테고리</th>
                    {compareList.map((item, index) => (
                      <th key={index} className="px-2 py-3 text-center text-sm font-medium text-gray-500">
                        <span
                          className="inline-block w-2 h-2 rounded-full mr-1"
                          style={{ backgroundColor: colors[index].replace('0.7', '1') }}
                        />
                        {item.address.split(' ').slice(-1)[0]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(categoryNames).map((key) => {
                    const scores = compareList.map((item) => (item.scores as any)[key].score);
                    const maxScore = Math.max(...scores);
                    return (
                      <tr key={key} className="border-t border-gray-100">
                        <td className="px-4 py-3 text-sm text-gray-700">{categoryNames[key]}</td>
                        {compareList.map((item, index) => {
                          const score = (item.scores as any)[key].score;
                          const isMax = score === maxScore && compareList.length > 1;
                          return (
                            <td key={index} className="px-2 py-3 text-center">
                              <span className={`font-medium ${isMax ? 'text-indigo-600' : 'text-gray-700'}`}>
                                {score}
                                {isMax && <span className="text-xs ml-1">👑</span>}
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                  <tr className="border-t-2 border-gray-200 bg-gray-50">
                    <td className="px-4 py-3 text-sm font-semibold text-gray-900">종합</td>
                    {compareList.map((item, index) => {
                      const isMax = item.score === Math.max(...compareList.map((i) => i.score)) && compareList.length > 1;
                      return (
                        <td key={index} className="px-2 py-3 text-center">
                          <span className={`font-bold ${isMax ? 'text-indigo-600' : 'text-gray-900'}`}>
                            {item.score}
                            {isMax && <span className="text-xs ml-1">👑</span>}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                </tbody>
              </table>
            </div>

            {/* 액션 버튼 */}
            <div className="flex gap-3">
              <button
                onClick={handleClearAll}
                className="flex-1 py-3 border border-gray-300 text-gray-700 font-semibold rounded-xl hover:bg-gray-50"
              >
                초기화
              </button>
              <button
                onClick={handleSaveComparison}
                className="flex-1 py-3 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700"
              >
                비교 저장
              </button>
            </div>
          </>
        )}
      </div>

      <BottomNav />
    </div>
  );
}
