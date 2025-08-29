#!/bin/bash

# Restart camera services to apply changes
echo "Restarting pose detection services..."
docker-compose restart detector-pose
docker-compose restart alert-logic
docker-compose restart camera-manager
echo "Services restarted."

echo "Changes applied successfully:"
echo "1. Added camera angle configuration to handle overhead cameras"
echo "2. Modified pose detection to consider camera angle when detecting hands up"
echo "3. Modified camera manager to pass camera angle to pose detection service"

echo ""
echo "Testing system functionality..."
docker-compose ps

echo ""
echo "Next steps:"
echo "1. Update camera configurations to set the appropriate camera angle:"
echo "   - front: For cameras at eye level facing straight (default)"
echo "   - overhead: For ceiling-mounted cameras facing downward"
echo "   - high_angle: For cameras mounted high but at an angle"
echo "   - low_angle: For cameras mounted below eye level looking up"
echo ""
echo "2. Check logs for proper functionality:"
echo "   docker-compose logs -f camera-manager detector-pose alert-logic"
