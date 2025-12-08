import React from 'react';
import { User, Palette, Globe, Monitor } from 'lucide-react';

const SettingsPage = () => {
    return (
        <div className="p-8 max-w-4xl mx-auto">
            <h1 className="text-2xl font-semibold text-gray-800 mb-6 flex items-center gap-2">
                <User className="text-[#d94838]" /> User Settings
            </h1>

            <div className="bg-white rounded-xl border border-gray-200 shadow-sm divide-y divide-gray-100">
                {/* Profile Section */}
                <div className="p-6">
                    <h2 className="text-lg font-medium text-gray-800 mb-4">Profile</h2>
                    <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-full bg-purple-600 flex items-center justify-center text-white text-xl font-bold">
                            SW
                        </div>
                        <div>
                            <div className="font-medium text-gray-900">swebber64</div>
                            <div className="text-sm text-gray-500">Administrator</div>
                        </div>
                        <button className="ml-auto text-sm border border-gray-300 px-3 py-1.5 rounded-lg hover:bg-gray-50 transition-colors">
                            Edit Profile
                        </button>
                    </div>
                </div>

                {/* Theme Section */}
                <div className="p-6">
                    <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2">
                        <Palette size={20} /> Appearance
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <button className="border-2 border-[#d94838] bg-gray-50 p-4 rounded-xl text-left relative overflow-hidden group">
                            <div className="absolute top-2 right-2 w-4 h-4 rounded-full bg-[#d94838] border border-white"></div>
                            <div className="font-medium text-gray-900">Light</div>
                            <div className="text-xs text-gray-500 mt-1">Default DHG theme</div>
                        </button>
                        <button className="border border-gray-200 p-4 rounded-xl text-left hover:border-gray-300 transition-colors">
                            <div className="font-medium text-gray-900">Dark</div>
                            <div className="text-xs text-gray-500 mt-1">Easy on the eyes</div>
                        </button>
                        <button className="border border-gray-200 p-4 rounded-xl text-left hover:border-gray-300 transition-colors">
                            <div className="font-medium text-gray-900">System</div>
                            <div className="text-xs text-gray-500 mt-1">Follow OS preference</div>
                        </button>
                    </div>
                </div>

                {/* Model Preference */}
                <div className="p-6">
                    <h2 className="text-lg font-medium text-gray-800 mb-4 flex items-center gap-2">
                        <Monitor size={20} /> Default Model
                    </h2>
                    <div className="max-w-md">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Primary Model for New Chats</label>
                        <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#d94838] focus:border-transparent">
                            <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                            <option value="gemini-1-5-pro">Gemini 1.5 Pro</option>
                            <option value="gpt-4o">GPT-4o</option>
                            <option value="llama-3-local">Llama 3 (Local)</option>
                        </select>
                        <p className="text-xs text-gray-500 mt-2">
                            This setting controls which model is selected by default when you start a new chat. You can always change it per chat.
                        </p>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default SettingsPage;
