import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BrainCircuit, Share2, Layers } from 'lucide-react';

const Home = () => {
    return (
        <div className="container mx-auto px-4 py-12">
            <div className="text-center max-w-3xl mx-auto mb-16">
                <h1 className="text-5xl font-extrabold text-primary mb-6 tracking-tight">
                    Teach Your AI <br />
                    <span className="text-accent bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-indigo-600">
                        Interact with the World
                    </span>
                </h1>
                <p className="text-xl text-secondary mb-8 leading-relaxed">
                    An interactive Edge AI system that learns from you. Teach objects, map actions, and share your models with the community.
                </p>
                <div className="flex justify-center gap-4">
                    <Link to="/learn" className="bg-accent hover:bg-blue-600 text-white px-8 py-3 rounded-xl font-semibold transition-all shadow-lg shadow-blue-500/20 flex items-center gap-2">
                        Start Teaching <ArrowRight className="w-4 h-4" />
                    </Link>
                    <Link to="/marketplace" className="bg-white hover:bg-slate-50 text-slate-700 px-8 py-3 rounded-xl font-semibold transition-all border border-slate-200 flex items-center gap-2">
                        Explore Models
                    </Link>
                </div>
            </div>

            <div className="grid md:grid-cols-3 gap-8 mt-12">
                {[
                    {
                        icon: BrainCircuit,
                        title: "Interactive Learning",
                        desc: "Show objects to the camera and teach the system instantly via voice or text."
                    },
                    {
                        icon: Layers,
                        title: "Incremental Intelligence",
                        desc: "The AI grows smarter over time. Correct its mistakes and refine its understanding."
                    },
                    {
                        icon: Share2,
                        title: "Model Marketplace",
                        desc: "Export your trained models and import specialized skills from other users."
                    }
                ].map((feature, i) => (
                    <div key={i} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
                        <div className="w-12 h-12 bg-blue-50 rounded-lg flex items-center justify-center mb-4">
                            <feature.icon className="w-6 h-6 text-accent" />
                        </div>
                        <h3 className="text-xl font-bold text-primary mb-2">{feature.title}</h3>
                        <p className="text-secondary">{feature.desc}</p>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Home;
