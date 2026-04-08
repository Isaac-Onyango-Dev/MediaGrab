import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Heart, ExternalLink, X, Coffee } from 'lucide-react';
import { SiGithub, SiOpencollective } from 'react-icons/si';

interface DonationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const DonationModal: React.FC<DonationModalProps> = ({ isOpen, onClose }) => {
  const kofiUrl = import.meta.env['VITE_KOFI_URL'] || '';
  const githubSponsorsUrl = import.meta.env['VITE_GITHUB_SPONSORS_URL'] || '';
  const openCollectiveUrl = import.meta.env['VITE_OPEN_COLLECTIVE_URL'] || '';

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-brand-950/80 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="glass-card p-6 md:p-8 rounded-3xl max-w-md w-full border-brand-electric/30"
          >
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-electric/20 flex items-center justify-center border border-brand-electric/30">
                  <Heart className="text-brand-electric" size={20} />
                </div>
                <h3 className="text-xl font-black text-white">Support MediaGrab</h3>
              </div>
              <button onClick={onClose} className="text-white/60 hover:text-white" aria-label="Close">
                <X size={24} />
              </button>
            </div>

            <p className="text-white/70 text-sm mb-6">
              Help keep MediaGrab free forever. Your support covers server costs and keeps development going.
            </p>

            {/* Donation Options */}
            <div className="space-y-4 mb-6">
              {/* Ko-fi Button */}
              {kofiUrl && (
                <a
                  href={kofiUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-4 rounded-xl bg-[#FF5E5B] text-white font-black text-lg hover:bg-[#FF5E5B]/80 transition-all flex items-center justify-center gap-3"
                >
                  <Coffee size={24} />
                  Buy me a coffee on Ko-fi
                  <ExternalLink size={18} />
                </a>
              )}

              {/* GitHub Sponsors Button */}
              {githubSponsorsUrl && (
                <a
                  href={githubSponsorsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-4 rounded-xl bg-slate-800 text-white font-black text-lg hover:bg-slate-700 transition-all flex items-center justify-center gap-3 border border-slate-700"
                >
                  <SiGithub size={24} />
                  Sponsor on GitHub
                  <ExternalLink size={18} />
                </a>
              )}

              {/* Open Collective Button */}
              {openCollectiveUrl && (
                <a
                  href={openCollectiveUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full py-4 rounded-xl bg-[#0F6D47] text-white font-black text-lg hover:bg-[#0F6D47]/80 transition-all flex items-center justify-center gap-3"
                >
                  <SiOpencollective size={24} />
                  Contribute on Open Collective
                  <ExternalLink size={18} />
                </a>
              )}
            </div>

            {/* Thank You Message */}
            <div className="text-center p-4 rounded-xl bg-brand-electric/10 border border-brand-electric/20">
              <p className="text-white/80 text-sm">
                Thank you for supporting MediaGrab!
              </p>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default DonationModal;
