'use client';

import { useState } from 'react';
import { Modal } from '@/shared/ui/modal';
import { walletApi } from '@/lib/api/wallet';
import { motion } from 'motion/react';
import { AlertTriangle, CheckCircle, Wallet, CreditCard, Coins } from 'lucide-react';
import { AxiosError } from 'axios';
import { markPerformance, measurePerformance, PerformanceMarks } from '@/shared/lib/web-vitals';

interface WithdrawalModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  currentBalance: number;
}

type ModalStep = 'form' | 'processing' | 'success' | 'error';
type PaymentMethod = 'crypto' | 'bank' | 'paypal';

export function WithdrawalModal({
  isOpen,
  onClose,
  onSuccess,
  currentBalance,
}: WithdrawalModalProps) {
  const [step, setStep] = useState<ModalStep>('form');
  const [error, setError] = useState('');

  // Form state
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('crypto');
  const [walletAddress, setWalletAddress] = useState('');
  const [bankAccount, setBankAccount] = useState('');
  const [paypalEmail, setPaypalEmail] = useState('');

  // Validation errors
  const [amountError, setAmountError] = useState('');
  const [addressError, setAddressError] = useState('');

  // Reset state on close
  const handleClose = () => {
    setStep('form');
    setError('');
    setAmount('');
    setWalletAddress('');
    setBankAccount('');
    setPaypalEmail('');
    setAmountError('');
    setAddressError('');
    onClose();
  };

  // Validate form
  const validateForm = (): boolean => {
    let isValid = true;
    setAmountError('');
    setAddressError('');

    const amountNum = parseFloat(amount);
    if (!amount || isNaN(amountNum) || amountNum <= 0) {
      setAmountError('Please enter a valid amount');
      isValid = false;
    } else if (amountNum > currentBalance) {
      setAmountError('Insufficient balance');
      isValid = false;
    } else if (amountNum < 10) {
      setAmountError('Minimum withdrawal amount is $10');
      isValid = false;
    }

    if (paymentMethod === 'crypto' && !walletAddress.trim()) {
      setAddressError('Please enter your wallet address');
      isValid = false;
    } else if (paymentMethod === 'bank' && !bankAccount.trim()) {
      setAddressError('Please enter your bank account number');
      isValid = false;
    } else if (paymentMethod === 'paypal' && !paypalEmail.trim()) {
      setAddressError('Please enter your PayPal email');
      isValid = false;
    }

    return isValid;
  };

  // Handle withdrawal
  const handleWithdraw = async () => {
    if (!validateForm()) return;

    // Mark start of withdrawal flow
    markPerformance(PerformanceMarks.WITHDRAWAL_FLOW_START, {
      amount: parseFloat(amount),
      method: paymentMethod,
    });

    setStep('processing');
    setError('');

    try {
      const withdrawalData: any = {
        amount: parseFloat(amount),
        method: paymentMethod,
      };

      // Add method-specific fields
      if (paymentMethod === 'crypto') {
        withdrawalData.wallet_address = walletAddress;
      } else if (paymentMethod === 'bank') {
        withdrawalData.bank_account = bankAccount;
      } else if (paymentMethod === 'paypal') {
        withdrawalData.paypal_email = paypalEmail;
      }

      await walletApi.requestWithdrawal(withdrawalData);
      setStep('success');

      // Mark completion of withdrawal flow
      markPerformance(PerformanceMarks.WITHDRAWAL_FLOW_COMPLETE, {
        amount: parseFloat(amount),
        method: paymentMethod,
      });

      // Measure total duration
      measurePerformance(
        'withdrawal-flow-duration',
        PerformanceMarks.WITHDRAWAL_FLOW_START,
        PerformanceMarks.WITHDRAWAL_FLOW_COMPLETE
      );

      // Auto-close and refresh after 2 seconds
      setTimeout(() => {
        onSuccess();
        handleClose();
      }, 2000);
    } catch (err) {
      setStep('error');
      if (err instanceof AxiosError) {
        const detail = err.response?.data?.detail;
        if (err.response?.status === 422) {
          setError(detail || 'Invalid withdrawal amount or insufficient balance');
        } else if (err.response?.status === 400) {
          setError(detail || 'Invalid withdrawal parameters');
        } else {
          setError(detail || 'Failed to request withdrawal');
        }
      } else {
        setError('An error occurred. Please try again.');
      }
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  };

  // Render form step
  if (step === 'form') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="WITHDRAW_FUNDS">
        <div className="space-y-6">
          {/* Balance Display */}
          <div className="cyber-card p-4 bg-terminal-surface/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Wallet className="h-5 w-5 text-neon-cyan" />
                <span className="text-sm text-muted-foreground">Available Balance</span>
              </div>
              <span className="text-xl font-display text-matrix-green">
                {formatCurrency(currentBalance)}
              </span>
            </div>
          </div>

          {/* Amount Input */}
          <div className="space-y-2">
            <label className="block text-sm font-mono text-muted-foreground">
              Withdrawal Amount
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground font-mono">
                $
              </span>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                min="10"
                max={currentBalance}
                step="0.01"
                className="w-full pl-8 pr-4 py-3 bg-terminal-surface border border-grid-line rounded font-mono text-sm focus:border-neon-cyan focus:outline-hidden transition-colors"
                aria-label="Withdrawal amount"
              />
            </div>
            {amountError && (
              <p className="text-xs text-red-500 font-mono">{amountError}</p>
            )}
            <p className="text-xs text-muted-foreground font-mono">
              Minimum: $10.00
            </p>
          </div>

          {/* Payment Method Selector */}
          <div className="space-y-3">
            <label className="block text-sm font-mono text-muted-foreground">
              Payment Method
            </label>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => setPaymentMethod('crypto')}
                className={`p-4 border rounded transition-all ${
                  paymentMethod === 'crypto'
                    ? 'bg-neon-cyan/20 border-neon-cyan/50 text-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.2)]'
                    : 'bg-terminal-bg border-grid-line/30 text-muted-foreground hover:border-neon-cyan/30'
                }`}
                aria-label="Crypto payment method"
              >
                <Coins className="h-6 w-6 mx-auto mb-2" />
                <span className="text-xs font-mono">Crypto</span>
              </button>
              <button
                onClick={() => setPaymentMethod('bank')}
                className={`p-4 border rounded transition-all ${
                  paymentMethod === 'bank'
                    ? 'bg-neon-cyan/20 border-neon-cyan/50 text-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.2)]'
                    : 'bg-terminal-bg border-grid-line/30 text-muted-foreground hover:border-neon-cyan/30'
                }`}
                aria-label="Bank transfer payment method"
              >
                <CreditCard className="h-6 w-6 mx-auto mb-2" />
                <span className="text-xs font-mono">Bank</span>
              </button>
              <button
                onClick={() => setPaymentMethod('paypal')}
                className={`p-4 border rounded transition-all ${
                  paymentMethod === 'paypal'
                    ? 'bg-neon-cyan/20 border-neon-cyan/50 text-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.2)]'
                    : 'bg-terminal-bg border-grid-line/30 text-muted-foreground hover:border-neon-cyan/30'
                }`}
                aria-label="PayPal payment method"
              >
                <Wallet className="h-6 w-6 mx-auto mb-2" />
                <span className="text-xs font-mono">PayPal</span>
              </button>
            </div>
          </div>

          {/* Payment Details */}
          <div className="space-y-2">
            {paymentMethod === 'crypto' && (
              <>
                <label className="block text-sm font-mono text-muted-foreground">
                  Crypto Wallet Address (USDT TRC20)
                </label>
                <input
                  type="text"
                  value={walletAddress}
                  onChange={(e) => setWalletAddress(e.target.value)}
                  placeholder="TXXXXxxxxx..."
                  className="w-full px-4 py-3 bg-terminal-surface border border-grid-line rounded font-mono text-sm focus:border-neon-cyan focus:outline-hidden transition-colors"
                  aria-label="Wallet address"
                />
              </>
            )}

            {paymentMethod === 'bank' && (
              <>
                <label className="block text-sm font-mono text-muted-foreground">
                  Bank Account Number
                </label>
                <input
                  type="text"
                  value={bankAccount}
                  onChange={(e) => setBankAccount(e.target.value)}
                  placeholder="XXXX-XXXX-XXXX"
                  className="w-full px-4 py-3 bg-terminal-surface border border-grid-line rounded font-mono text-sm focus:border-neon-cyan focus:outline-hidden transition-colors"
                  aria-label="Bank account number"
                />
              </>
            )}

            {paymentMethod === 'paypal' && (
              <>
                <label className="block text-sm font-mono text-muted-foreground">
                  PayPal Email Address
                </label>
                <input
                  type="email"
                  value={paypalEmail}
                  onChange={(e) => setPaypalEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full px-4 py-3 bg-terminal-surface border border-grid-line rounded font-mono text-sm focus:border-neon-cyan focus:outline-hidden transition-colors"
                  aria-label="PayPal email"
                />
              </>
            )}
            {addressError && (
              <p className="text-xs text-red-500 font-mono">{addressError}</p>
            )}
          </div>

          {/* Warning */}
          <div className="p-4 bg-neon-pink/5 border border-neon-pink/30 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-neon-pink flex-shrink-0 mt-0.5" />
              <div className="flex-1 space-y-1">
                <p className="text-sm font-semibold text-neon-pink">
                  Withdrawal Notice
                </p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Withdrawals are processed within 24-48 hours after admin approval. Please ensure your payment details are correct.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleClose}
              className="flex-1 px-4 py-3 bg-terminal-bg hover:bg-terminal-surface border border-grid-line/50 text-muted-foreground font-mono text-sm rounded transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleWithdraw}
              className="flex-1 px-4 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors hover:shadow-[0_0_15px_rgba(0,255,255,0.3)]"
            >
              Request Withdrawal
            </button>
          </div>
        </div>
      </Modal>
    );
  }

  // Render processing step
  if (step === 'processing') {
    return (
      <Modal isOpen={isOpen} onClose={() => {}} title="PROCESSING_WITHDRAWAL">
        <div className="text-center py-8 space-y-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          >
            <div className="h-12 w-12 border-4 border-neon-cyan border-t-transparent rounded-full mx-auto" />
          </motion.div>
          <p className="text-sm text-muted-foreground font-mono">
            Processing withdrawal request...
          </p>
        </div>
      </Modal>
    );
  }

  // Render success step
  if (step === 'success') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="WITHDRAWAL_SUCCESS">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="text-center space-y-6 py-8"
        >
          <CheckCircle className="h-16 w-16 text-matrix-green mx-auto" />
          <div className="space-y-2">
            <h3 className="text-lg font-display text-matrix-green">
              Withdrawal Request Submitted
            </h3>
            <p className="text-sm text-muted-foreground">
              Your withdrawal request has been submitted successfully
            </p>
            <p className="text-xs text-muted-foreground font-mono mt-3">
              Processing time: 24-48 hours
            </p>
          </div>
        </motion.div>
      </Modal>
    );
  }

  // Render error step
  if (step === 'error') {
    return (
      <Modal isOpen={isOpen} onClose={handleClose} title="WITHDRAWAL_ERROR">
        <div className="text-center space-y-6 py-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', bounce: 0.5 }}
          >
            <AlertTriangle className="h-16 w-16 text-red-500 mx-auto" />
          </motion.div>
          <div className="space-y-2">
            <h3 className="text-lg font-display text-red-500">
              Withdrawal Failed
            </h3>
            <p className="text-sm text-muted-foreground">
              {error || 'Failed to process withdrawal request'}
            </p>
          </div>
          <button
            onClick={() => setStep('form')}
            className="px-6 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors"
          >
            Try Again
          </button>
        </div>
      </Modal>
    );
  }

  return null;
}
