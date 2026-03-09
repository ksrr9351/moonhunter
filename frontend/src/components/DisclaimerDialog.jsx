import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';

export const DisclaimerDialog = ({ variant = 'button' }) => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {variant === 'link' ? (
          <button className="footer-link-fixed">
            Disclaimer
          </button>
        ) : (
          <Button className="btn-secondary" style={{ padding: '14px 24px', fontSize: '18px' }}>
            Disclaimer
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh] bg-[#121212] border border-[rgba(255,255,255,0.25)] text-white">
        <DialogHeader>
          <DialogTitle className="text-2xl font-semibold text-[#00FFD1]">
            Moon Hunters – Key Risks Disclosure
          </DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-[60vh] pr-4">
          <DialogDescription className="text-[rgba(255,255,255,0.85)] space-y-4 text-left">
            <p>
              Investing in Moon Hunters ($MHUNT) exposes you to several material risks. You should carefully assess whether you understand these risks and whether you can afford to take them. By interacting with Moon Hunters, its AI-agent investment strategy, staking mechanics, or token, you acknowledge that you may lose the entire value of your investment.
            </p>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">1. You Could Lose All the Money You Invest</h3>
              <p>
                The value of Moon Hunters' token and its underlying AI-managed portfolio can rise and fall rapidly. Cryptoassets are inherently volatile, and prices can move without clear explanations or transparent market mechanisms. You should be prepared to lose 100% of the amount you invest.
              </p>
              <p className="mt-2">
                Losses may also occur due to:
              </p>
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li>Sharp market downturns</li>
                <li>Liquidity shocks</li>
                <li>Trading failures at underlying decentralized exchanges</li>
                <li>AI-driven investment decisions that perform below expectations</li>
              </ul>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">2. Technology, Cybersecurity, and Operational Risks</h3>
              <p>
                Investing in Moon Hunters exposes you to risks associated with:
              </p>
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li>Cyber-attacks, smart-contract exploits, validator hijacking, or wallet breaches</li>
                <li>Operational failures, such as AI model malfunction, protocol downtime, or infrastructure outages</li>
                <li>Smart contract vulnerabilities, coding errors, or security flaws</li>
                <li>Financial crime risks, including fraud or unauthorized access</li>
              </ul>
              <p className="mt-2">
                If such events occur, you may not be able to recover your funds or cryptoassets.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">3. Staking and Slashing Risks</h3>
              <p>
                If you stake $MHUNT or other assets via Moon Hunters:
              </p>
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li>Certain blockchain protocols impose slashing penalties for validator errors, downtime, or malicious behavior.</li>
                <li>Slashing can result in partial or full loss of staked tokens.</li>
                <li>Some staking mechanisms involve lock-up periods, preventing immediate withdrawal.</li>
              </ul>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">4. You Should Not Expect Regulatory Protection</h3>
              <p>
                Moon Hunters operates in the cryptoasset sphere, largely outside traditional regulatory protections:
              </p>
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li>Your investment is not covered by any compensation scheme.</li>
                <li>You cannot rely on traditional financial ombudsman services.</li>
                <li>Losses due to market events, failures, or fraud are unlikely to be recoverable.</li>
              </ul>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">5. Liquidity Risk – You May Not Be Able to Sell When You Want</h3>
              <p>
                There is no guarantee you can sell your $MHUNT tokens quickly or at a desirable price.
              </p>
              <p className="mt-2">
                Liquidity may be affected by:
              </p>
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li>Low trading volume</li>
                <li>Market volatility</li>
                <li>Protocol downtime</li>
                <li>Bonding-curve limitations</li>
                <li>Network congestion or outages</li>
              </ul>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">6. Fraud, Scams, and Malicious Activity</h3>
              <p>
                The crypto ecosystem is frequently targeted by:
              </p>
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li>Phishing</li>
                <li>Impersonation</li>
                <li>Fake investment schemes</li>
                <li>Malware</li>
                <li>Social engineering</li>
              </ul>
              <p className="mt-2">
                Moon Hunters implements best practices but cannot guarantee complete protection. You must remain vigilant.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">7. AI-Driven Investment Complexity</h3>
              <p>
                Moon Hunters uses AI models that:
              </p>
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li>May produce inaccurate predictions</li>
                <li>May react unexpectedly during volatile events</li>
                <li>May rely on incomplete or manipulated data</li>
              </ul>
              <p className="mt-2">
                Do not assume AI will outperform markets or ensure gains.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">8. User Responsibility for Wallet and Device Security</h3>
              <p>
                You must ensure:
              </p>
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li>Safe storage of private keys</li>
                <li>Protection of seed phrases and authentication devices</li>
                <li>Secure internet connections</li>
                <li>Software updates</li>
              </ul>
              <p className="mt-2">
                Losses due to personal security mistakes are irreversible.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">9. Concentration Risk</h3>
              <p>
                Investing heavily in a single cryptoasset (such as Moon Hunters) increases loss risk.
                Diversification reduces exposure.
              </p>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-white mb-2">10. Different Cryptoassets Carry Different Risks</h3>
              <p>
                Moon Hunters interacts with various cryptoassets that each have:
              </p>
              <ul className="list-disc list-inside ml-4 mt-2 space-y-1">
                <li>Different volatility</li>
                <li>Different liquidity</li>
                <li>Different technical designs</li>
                <li>Different regulatory implications</li>
              </ul>
              <p className="mt-2">
                Understand each asset before investing.
              </p>
            </div>
          </DialogDescription>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
};