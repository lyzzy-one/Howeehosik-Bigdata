'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import BottomNav from '@/components/BottomNav';

interface HistoryItem {
  id: number;
  address: string;
  lat: string;
  lng: string;
  score: number;
  grade: string;
  date: string;
}

function getGradeColor(grade: string): string {
  switch (grade) {
    case 'A': return 'text-green-600 bg-green-100';
    case 'B': return 'text-blue-600 bg-blue-100';
    case 'C': return 'text-yellow-600 bg-yellow-100';
    case 'D': return 'text-orange-600 bg-orange-100';
    default: return 'text-red-600 bg-red-100';
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return '오늘';
  if (diffDays === 1) return '어제';
  if (diffDays < 7) return `${diffDays}일 전`;

  return `${date.getMonth() + 1}월 ${date.getDate()}일`;
}

export default function HistoryPage() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const router = useRouter();

  useEffect(() => {
    const saved = localStorage.getItem('search_history');
    if (saved) {
      // 30일 이내 기록만 필터링
      const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
      const filtered = JSON.parse(saved).filter(
        (item: HistoryItem) => new Date(item.date).getTime() > thirtyDaysAgo
      );
      setHistory(filtered);
    }
  }, []);

  const handleDelete = (id: number) => {
    const newHistory = history.filter((item) => item.id !== id);
    setHistory(newHistory);
    localStorage.setItem('search_history', JSON.stringify(newHistory));
  };

  const handleClearAll = () => {
    if (confirm('모든 기록을 삭제하시겠습니까?')) {
      setHistory([]);
      localStorage.removeItem('search_history');
    }
  };

  const handleItemClick = (item: HistoryItem) => {
    const params = new URLSearchParams({
      lat: item.lat,
      lng: item.lng,
      address: item.address,
    });
    router.push(`/result?${params.toString()}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <Header title="검색 기록" showBack />

      <div className="max-w-lg mx-auto p-4">
        {history.length === 0 ? (
          <div className="bg-white rounded-xl p-8 text-center">
            <div className="text-4xl mb-4">📋</div>
            <h3 className="font-semibold text-gray-900 mb-2">검색 기록이 없어요</h3>
            <p className="text-gray-500 text-sm mb-4">
              주소를 검색하고 저장하면<br />여기에 기록이 남아요
            </p>
            <button
              onClick={() => router.push('/')}
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              주소 검색하기
            </button>
          </div>
        ) : (
          <>
            {/* 헤더 */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-gray-500">최근 30일 기록</span>
              <button
                onClick={handleClearAll}
                className="text-sm text-red-500 hover:text-red-600"
              >
                전체 삭제
              </button>
            </div>

            {/* 기록 목록 */}
            <div className="space-y-3">
              {history.map((item) => (
                <div
                  key={item.id}
                  className="bg-white rounded-xl p-4 shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <button
                      onClick={() => handleItemClick(item)}
                      className="flex-1 text-left"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg font-bold text-gray-900">{item.score}점</span>
                        <span className={`px-2 py-0.5 rounded text-sm font-medium ${getGradeColor(item.grade)}`}>
                          {item.grade}
                        </span>
                      </div>
                      <div className="text-gray-700">{item.address}</div>
                      <div className="text-sm text-gray-400 mt-1">{formatDate(item.date)}</div>
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      className="p-2 text-gray-400 hover:text-red-500"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <BottomNav />
    </div>
  );
}
