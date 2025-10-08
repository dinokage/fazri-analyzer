'use client';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Entity } from '@/types/entity';
import { Badge } from '@/components/ui/badge';

interface EntityProfileProps {
  entity: Entity;
}

export function EntityProfile({ entity }: EntityProfileProps) {
  const initials = entity.name
    ?.split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase() || '??';

    const face_id = entity.identifiers.filter(id => id.type === 'face_id')[0]?.value || null;
    const imageUrl = face_id ? process.env.NEXT_PUBLIC_CDN_URL+`/${face_id}.jpg` : "";

  return (
    <div className="bg-[#14141a] rounded-lg border border-gray-800 p-6">
      <h2 className="text-lg font-semibold mb-6">Entity Profile</h2>
      
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Avatar className="h-16 w-16">
            <AvatarImage src={imageUrl} />
            <AvatarFallback className="bg-blue-600 text-white text-xl">
              {initials}
            </AvatarFallback>
          </Avatar>
          
          <div>
            <h3 className="text-xl font-semibold">{entity.name || 'Unknown'}</h3>
            <p className="text-gray-400">{entity.entity_type || 'Student'}</p>
            {entity.department && (
              <p className="text-sm text-gray-500 mt-1">{entity.department}</p>
            )}
          </div>
        </div>

        <div className="text-right">
          <p className="text-sm text-gray-400 mb-2">Recent Alerts</p>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="sm"
              className="bg-[#1a1a24] border-gray-700 hover:bg-[#242430]"
            >
              Acknowledge
            </Button>
            <Button 
              variant="outline" 
              size="sm"
              className="bg-[#1a1a24] border-gray-700 hover:bg-[#242430]"
            >
              Dismiss
            </Button>
          </div>
        </div>
      </div>

      {entity.identifiers && entity.identifiers.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <p className="text-sm text-gray-400 mb-2">Identifiers</p>
          <div className="flex flex-wrap gap-2">
            {entity.identifiers.slice(0, 3).map((identifier, idx) => (
              <Badge 
                key={idx} 
                variant="secondary"
                className="bg-[#1a1a24] text-gray-300"
              >
                {identifier.type}: {identifier.value}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}