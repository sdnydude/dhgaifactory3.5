import React, { useState } from 'react';
import { Key, BarChart3, Database, Shield } from 'lucide-react';

const AdminPage = () => {
    const [apiKeys, setApiKeys] = useState([
        { id: 1, provider: 'OpenAI', maskedKey: 'sk-....4f9a', active: true },
        { id: 2, provider: 'Anthropic', maskedKey: 'sk-ant-....9d21', active: true },
        { id: 3, provider: 'Google Gemini', maskedKey: '', active: false },
    ]);

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8">
            <h1 className="text-2xl font-semibold text-gray-800 flex items-center gap-2">
                <Shield className="text-[#d94838]" /> Admin Dashboard
            </h1>

            {/* Stats Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
                    <div className="text-sm font-medium text-gray-500 mb-1">Total Requests</div>
                    <div className="text-2xl font-bold text-gray-800">1,248</div>
                    <div className="text-xs text-green-600 mt-2 flex items-center gap-1">
                        <BarChart3 size={12} /> +12% from last week
                    </div>
                </div>
                <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
                    <div className="text-sm font-medium text-gray-500 mb-1">Active Agents</div>
                    <div className="text-2xl font-bold text-gray-800">7/9</div>
                    <div className="text-xs text-gray-400 mt-2">2 maintenance mode</div>
                </div>
                <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
                    <div className="text-sm font-medium text-gray-500 mb-1">Cost Est. (MTD)</div>
                    <div className="text-2xl font-bold text-gray-800">$14.20</div>
                    <div className="text-xs text-gray-400 mt-2">Based on token usage</div>
                </div>
            </div>

            {/* API Key Management */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                    <h2 className="font-semibold text-gray-700 flex items-center gap-2">
                        <Key size={18} /> API Key Management
                    </h2>
                    <button className="text-sm bg-[#d94838] text-white px-3 py-1.5 rounded-lg hover:bg-[#c3392b] transition-colors">
                        Add New Key
                    </button>
                </div>
                <div className="p-6">
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm text-left">
                            <thead className="text-gray-500 bg-gray-50 font-medium border-b border-gray-100">
                                <tr>
                                    <th className="px-4 py-3">Provider</th>
                                    <th className="px-4 py-3">Key (Masked)</th>
                                    <th className="px-4 py-3">Status</th>
                                    <th className="px-4 py-3 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {apiKeys.map((key) => (
                                    <tr key={key.id} className="hover:bg-gray-50/50">
                                        <td className="px-4 py-3 font-medium text-gray-800">{key.provider}</td>
                                        <td className="px-4 py-3 text-gray-500 font-mono">{key.maskedKey || 'Not configured'}</td>
                                        <td className="px-4 py-3">
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${key.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                                                }`}>
                                                {key.active ? 'Active' : 'Inactive'}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <button className="text-blue-600 hover:text-blue-800 mr-3">Edit</button>
                                            <button className="text-red-500 hover:text-red-700">Delete</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* System Status Mock */}
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
                    <h2 className="font-semibold text-gray-700 flex items-center gap-2">
                        <Database size={18} /> System Health
                    </h2>
                </div>
                <div className="p-6">
                    <div className="space-y-3">
                        <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-100">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                                <span className="font-medium text-green-800">Orchestrator Agent</span>
                            </div>
                            <span className="text-sm text-green-600">Healthy (20ms latency)</span>
                        </div>
                        <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg border border-red-100">
                            <div className="flex items-center gap-3">
                                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                                <span className="font-medium text-red-800">Competitor Intel Agent</span>
                            </div>
                            <span className="text-sm text-red-600">Offline (Connection Refused)</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AdminPage;
