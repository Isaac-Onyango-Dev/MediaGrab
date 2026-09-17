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
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-ink/70 p-4" onClick={onClose}>
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            role="dialog" aria-modal="true" aria-labelledby="donate-title" onClick={(e) => e.stopPropagation()}
            className="w-full max-w-md rounded-[28px] border-2 border-ink bg-glass p-6 text-ink shadow-[0_10px_0_var(--color-ink)] md:p-8"
          >
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl border-2 border-ink bg-capsule">
                  <Heart size={20} />
                </div>
                <h3 id="donate-title" className="display text-2xl">Support MediaGrab</h3>
              </div>
              <button onClick={onClose} className="rounded-lg p-1 text-ink-soft hover:text-ink" aria-label="Close">
                <X size={24} />
              </button>
            </div>

            <p className="mb-6 text-ink-soft">
              MediaGrab stays free and ad-free. Pick whichever way of chipping in suits you.
            </p>

            {/* Donation Options */}
            <div className="space-y-4 mb-6">
              {/* Ko-fi Button */}
              {kofiUrl && (
                <a
                  href={kofiUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="arcade-btn w-full bg-[#FF5E5B] py-3.5 text-lg text-white"
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
                  className="arcade-btn w-full bg-ink py-3.5 text-lg text-white"
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
                  className="arcade-btn w-full bg-[#0F6D47] py-3.5 text-lg text-white"
                >
                  <SiOpencollective size={24} />
                  Contribute on Open Collective
                  <ExternalLink size={18} />
                </a>
              )}
            </div>

            {/* Thank You Message */}
            <div className="rounded-xl bg-prize p-4 text-center">
              <p className="text-sm font-semibold">
                {kofiUrl || githubSponsorsUrl || openCollectiveUrl
                  ? 'Thank you for keeping MediaGrab going.'
                  : 'Donation links aren’t set up yet. Starring the repo on GitHub helps too.'}
              </p>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default DonationModal;
