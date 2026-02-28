import React from 'react';
import { NavLink } from 'react-router-dom';
import { BrainCircuit, BookOpen, Eye, ShoppingBag } from 'lucide-react';

const Header = () => {
    const navItems = [
        { name: 'Learn', path: '/learn', icon: BookOpen },
        { name: 'Infer', path: '/infer', icon: Eye },
        { name: 'Marketplace', path: '/marketplace', icon: ShoppingBag },
    ];

    return (
        <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                <NavLink to="/" className="flex items-center gap-2 text-primary font-bold text-xl">
                    <BrainCircuit className="w-8 h-8 text-accent" />
                    <span>IntelShare<span className="text-accent">AI</span></span>
                </NavLink>

                <nav className="flex items-center gap-6">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.name}
                            to={item.path}
                            className={({ isActive }) =>
                                `flex items-center gap-2 px-3 py-2 rounded-lg transition-colors font-medium ${isActive
                                    ? 'bg-accent/10 text-accent'
                                    : 'text-slate-600 hover:text-primary hover:bg-slate-50'
                                }`
                            }
                        >
                            <item.icon className="w-4 h-4" />
                            <span>{item.name}</span>
                        </NavLink>
                    ))}
                </nav>
            </div>
        </header>
    );
};

export default Header;
