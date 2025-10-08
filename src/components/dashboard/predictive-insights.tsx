// components/dashboard/predictive-insights.tsx
'use client';

import { MapPin, TrendingUp, Clock, AlertCircle, Info, Brain, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { format } from 'date-fns';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';

interface PredictionExplanation {
  confidence_level: string;
  evidence: string[];
  key_factors: string[];
  reasoning: string;
}

interface LocationPrediction {
  location: string;
  confidence: number;
  explanation: PredictionExplanation;
}

export interface PredictionData {
  entity_id: string;
  target_time: string;
  predictions: LocationPrediction[];
  method: string;
}

interface PredictiveInsightsProps {
  prediction: PredictionData | null;
}

export function PredictiveInsights({ prediction }: PredictiveInsightsProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [selectedPrediction, setSelectedPrediction] = useState<LocationPrediction | null>(null);

  // Get confidence level color
  const getConfidenceColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'high':
        return 'text-green-500';
      case 'medium':
        return 'text-yellow-500';
      case 'low':
        return 'text-orange-500';
      default:
        return 'text-gray-500';
    }
  };

  // Get confidence badge color
  const getConfidenceBadgeColor = (confidence: number) => {
    if (confidence >= 0.7) return 'bg-green-600';
    if (confidence >= 0.5) return 'bg-yellow-600';
    if (confidence >= 0.3) return 'bg-orange-600';
    return 'bg-red-600';
  };

  // Format method name
  const formatMethod = (method: string) => {
    if (!method) return 'Unknown Method';
    return method
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Format confidence level
  const formatConfidenceLevel = (level: string) => {
    if (!level) return 'Unknown';
    return level.charAt(0).toUpperCase() + level.slice(1);
  };

  // Get method icon
  const getMethodIcon = (method: string) => {
    const methodLower = method?.toLowerCase() || '';
    if (methodLower.includes('ml') || methodLower.includes('model')) return <Brain className="h-4 w-4" />;
    if (methodLower.includes('pattern')) return <TrendingUp className="h-4 w-4" />;
    if (methodLower.includes('fallback') || methodLower.includes('last')) return <AlertCircle className="h-4 w-4" />;
    return <Zap className="h-4 w-4" />;
  };

  // Handle no prediction data
  if (!prediction) {
    return (
      <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-6">Predictive Insights</h2>
        <Alert className="bg-[#1a1a24] border-gray-700">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No prediction data available. Location prediction requires sufficient historical activity data.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Handle empty predictions array
  if (!prediction.predictions || prediction.predictions.length === 0) {
    return (
      <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
        <h2 className="text-lg font-semibold mb-6">Predictive Insights</h2>
        <Alert className="bg-[#1a1a24] border-gray-700">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Unable to generate location predictions. More historical data may be needed.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  // Get primary prediction (first one with highest confidence)
  const primaryPrediction = prediction.predictions.reduce((prev, current) => 
    (current.confidence > prev.confidence) ? current : prev
  );

  // Get alternative predictions
  const alternativePredictions = prediction.predictions
    .filter(p => p !== primaryPrediction)
    .sort((a, b) => b.confidence - a.confidence);

  return (
    <>
      <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">Predictive Insights</h2>
          <div className="flex items-center gap-2 text-xs text-gray-400">
            {getMethodIcon(prediction.method)}
            <span>{formatMethod(prediction.method)}</span>
          </div>
        </div>
        
        {/* Map visualization area */}
        <div className="relative h-64 bg-gradient-to-br from-blue-950/30 to-purple-950/30 rounded-lg mb-4 flex items-center justify-center overflow-hidden">
          {/* Background pattern */}
          <div className="absolute inset-0 opacity-10">
            <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="0.5"/>
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#grid)" />
            </svg>
          </div>

          {/* Main prediction marker */}
          <div className="relative text-center z-10">
            <div className={cn(
              "w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-2 shadow-lg",
              primaryPrediction.confidence >= 0.7 ? "bg-green-600 shadow-green-500/50 animate-pulse" :
              primaryPrediction.confidence >= 0.5 ? "bg-yellow-600 shadow-yellow-500/50 animate-pulse" :
              "bg-orange-600 shadow-orange-500/50 animate-pulse"
            )}>
              <MapPin className="h-6 w-6" />
            </div>
            <p className="text-white font-medium text-lg">
              {primaryPrediction.location || 'Unknown Location'}
            </p>
            {prediction.target_time && (
              <p className="text-gray-400 text-sm mt-1">
                {format(new Date(prediction.target_time), 'MMM dd, h:mm a')}
              </p>
            )}
          </div>

          {/* Alternative location indicators */}
          {alternativePredictions.slice(0, 2).map((alt, idx) => (
            <div
              key={idx}
              className="absolute cursor-pointer hover:scale-110 transition-transform"
              style={{
                top: `${30 + idx * 25}%`,
                left: `${20 + idx * 40}%`,
              }}
              onClick={() => {
                setSelectedPrediction(alt);
                setShowDetails(true);
              }}
            >
              <div className="w-8 h-8 bg-blue-400/30 rounded-full flex items-center justify-center border border-blue-500/50 hover:bg-blue-400/50">
                <MapPin className="h-4 w-4 text-blue-300" />
              </div>
            </div>
          ))}
        </div>

        {/* Primary prediction details */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <h3 className="font-medium mb-1">Predicted Location</h3>
              <p className="text-sm text-gray-400 flex items-center gap-2">
                <span className={getConfidenceColor(primaryPrediction.explanation?.confidence_level || '')}>
                  {formatConfidenceLevel(primaryPrediction.explanation?.confidence_level || 'unknown')} confidence
                </span>
                <span className="text-gray-600">•</span>
                <span>{(primaryPrediction.confidence * 100).toFixed(0)}%</span>
              </p>
            </div>
            <Button 
              variant="outline"
              size="sm"
              className="bg-[#1a1a24] border-gray-700 hover:bg-[#242430]"
              onClick={() => {
                setSelectedPrediction(primaryPrediction);
                setShowDetails(true);
              }}
            >
              DETAIL
            </Button>
          </div>

          {/* Confidence bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-gray-400">
              <span>Confidence Score</span>
              <span>{(primaryPrediction.confidence * 100).toFixed(1)}%</span>
            </div>
            <Progress 
              value={primaryPrediction.confidence * 100} 
              className="h-2"

            />
          </div>

          {/* Quick factors preview */}
          {primaryPrediction.explanation?.key_factors && 
           primaryPrediction.explanation.key_factors.length > 0 && (
            <div className="pt-4 border-t border-gray-800">
              <p className="text-xs text-gray-400 mb-2">Key Factors:</p>
              <div className="flex flex-wrap gap-2">
                {primaryPrediction.explanation.key_factors.slice(0, 3).map((factor, idx) => (
                  <Badge
                    key={idx}
                    variant="secondary"
                    className="bg-[#1a1a24] text-gray-300 text-xs"
                  >
                    {factor.replace(/_/g, ' ')}
                  </Badge>
                ))}
                {primaryPrediction.explanation.key_factors.length > 3 && (
                  <Badge
                    variant="secondary"
                    className="bg-[#1a1a24] text-gray-400 text-xs"
                  >
                    +{primaryPrediction.explanation.key_factors.length - 3} more
                  </Badge>
                )}
              </div>
            </div>
          )}

          {/* Alternative locations */}
          {alternativePredictions.length > 0 && (
            <div className="pt-4 border-t border-gray-800">
              <p className="text-xs text-gray-400 mb-2">Alternative Locations:</p>
              <div className="space-y-2">
                {alternativePredictions.slice(0, 3).map((alt, idx) => (
                  <div 
                    key={idx} 
                    className="flex items-center justify-between text-sm bg-[#1a1a24] rounded p-2 cursor-pointer hover:bg-[#242430] transition-colors"
                    onClick={() => {
                      setSelectedPrediction(alt);
                      setShowDetails(true);
                    }}
                  >
                    <span className="text-gray-300">{alt.location}</span>
                    <Badge 
                      variant="secondary" 
                      className={cn("text-xs", getConfidenceBadgeColor(alt.confidence))}
                    >
                      {(alt.confidence * 100).toFixed(0)}%
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Details Dialog */}
      <Dialog open={showDetails} onOpenChange={setShowDetails}>
        <DialogContent className="bg-[#14141a] border-gray-800 max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Prediction Details</DialogTitle>
            <DialogDescription>
              Detailed breakdown of location prediction for {prediction.entity_id}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6">
            {/* Selected prediction or primary */}
            {(() => {
              const displayPrediction = selectedPrediction || primaryPrediction;
              return (
                <>
                  {/* Main prediction info */}
                  <div>
                    <h4 className="font-medium mb-3 flex items-center gap-2">
                      <MapPin className="h-4 w-4" />
                      Predicted Location
                    </h4>
                    <div className="bg-[#1a1a24] rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-lg font-medium">{displayPrediction.location}</span>
                        <Badge className={getConfidenceBadgeColor(displayPrediction.confidence)}>
                          {(displayPrediction.confidence * 100).toFixed(1)}%
                        </Badge>
                      </div>
                      {prediction.target_time && (
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                          <Clock className="h-3 w-3" />
                          Target: {format(new Date(prediction.target_time), 'PPpp')}
                        </div>
                      )}
                      {displayPrediction.explanation && (
                        <div className="mt-3 pt-3 border-t border-gray-700">
                          <div className="flex items-center gap-2 text-sm">
                            <span className="text-gray-400">Confidence Level:</span>
                            <span className={getConfidenceColor(displayPrediction.explanation.confidence_level)}>
                              {formatConfidenceLevel(displayPrediction.explanation.confidence_level)}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Reasoning */}
                  {displayPrediction.explanation?.reasoning && (
                    <div>
                      <h4 className="font-medium mb-3 flex items-center gap-2">
                        <Info className="h-4 w-4" />
                        Reasoning
                      </h4>
                      <div className="bg-[#1a1a24] rounded-lg p-4">
                        <p className="text-sm text-gray-300">
                          {displayPrediction.explanation.reasoning}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Key factors */}
                  {displayPrediction.explanation?.key_factors && 
                   displayPrediction.explanation.key_factors.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-3 flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        Key Factors
                      </h4>
                      <div className="grid grid-cols-2 gap-3">
                        {displayPrediction.explanation.key_factors.map((factor, idx) => (
                          <div key={idx} className="bg-[#1a1a24] rounded-lg p-3">
                            <p className="text-sm capitalize">
                              {factor.replace(/_/g, ' ')}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Evidence */}
                  {displayPrediction.explanation?.evidence && 
                   displayPrediction.explanation.evidence.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-3">Supporting Evidence</h4>
                      <div className="bg-[#1a1a24] rounded-lg p-4 space-y-2">
                        {displayPrediction.explanation.evidence.map((item, idx) => (
                          <div key={idx} className="flex items-start gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
                            <p className="text-sm text-gray-300">{item}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Method info */}
                  <div>
                    <h4 className="font-medium mb-3">Prediction Method</h4>
                    <div className="bg-[#1a1a24] rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        {getMethodIcon(prediction.method)}
                        <span className="font-medium">{formatMethod(prediction.method)}</span>
                      </div>
                      <p className="text-xs text-gray-400">
                        {prediction.method === 'last_known_fallback' 
                          ? 'Using the last known location as a fallback when insufficient data is available for pattern-based predictions.'
                          : prediction.method === 'pattern_based'
                          ? 'Using historical activity patterns and machine learning to predict the most likely location.'
                          : 'Advanced prediction method combining multiple data sources and algorithms.'
                        }
                      </p>
                    </div>
                  </div>

                  {/* All predictions comparison */}
                  {prediction.predictions.length > 1 && (
                    <div>
                      <h4 className="font-medium mb-3">All Predictions</h4>
                      <div className="space-y-2">
                        {prediction.predictions
                          .sort((a, b) => b.confidence - a.confidence)
                          .map((pred, idx) => (
                            <div 
                              key={idx}
                              className={cn(
                                "bg-[#1a1a24] rounded-lg p-3 flex justify-between items-center",
                                pred === displayPrediction && "border border-blue-500"
                              )}
                            >
                              <div>
                                <span className="font-medium">{pred.location}</span>
                                <span className="text-xs text-gray-400 ml-2">
                                  ({formatConfidenceLevel(pred.explanation?.confidence_level || '')})
                                </span>
                              </div>
                              <Badge 
                                variant="secondary" 
                                className={getConfidenceBadgeColor(pred.confidence)}
                              >
                                {(pred.confidence * 100).toFixed(0)}%
                              </Badge>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Raw data for debugging */}
                  <details className="mt-4">
                    <summary className="cursor-pointer text-sm text-gray-400 hover:text-gray-300">
                      View Raw Prediction Data
                    </summary>
                    <pre className="text-xs bg-[#1a1a24] p-4 rounded mt-2 overflow-x-auto">
                      {JSON.stringify(prediction, null, 2)}
                    </pre>
                  </details>
                </>
              );
            })()}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

// Add missing import
import { cn } from '@/lib/utils';