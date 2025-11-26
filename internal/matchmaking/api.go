package matchmaking

import (
	"context"
	"fmt"
	"net"
	"sync"
	"time"

	"cukiller/internal/matchmaking/pb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/types/known/emptypb"
)

type matchmakingServer struct {
	pb.UnimplementedMatchmakingServiceServer
}

func StartupGrpc() {
	addr := fmt.Sprintf(":%d", conf.Port)
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		logger.Error("Failed to bind gRPC listener: %v", err)
		return
	}

	server := grpc.NewServer()
	pb.RegisterMatchmakingServiceServer(server, &matchmakingServer{})

	logger.Info("gRPC server starting on %s", addr)
	if err := server.Serve(lis); err != nil {
		logger.Error("gRPC server failed: %v", err)
	}
}

func cleanQueues() {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()
	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	KillerPool = make(map[uint64]QueuePlayer)
	VictimPool = make(map[uint64]QueuePlayer)
}

func (s *matchmakingServer) Ping(ctx context.Context, _ *pb.PingRequest) (*pb.PingResponse, error) {
	logger.Info("Ping request received")
	return &pb.PingResponse{Message: "ok"}, nil
}

func (s *matchmakingServer) Health(ctx context.Context, _ *pb.HealthRequest) (*pb.HealthResponse, error) {
	logger.Info("Health request received")
	return &pb.HealthResponse{
		Status:        "healthy",
		TimestampUnix: time.Now().Unix(),
	}, nil
}

func (s *matchmakingServer) AddPlayer(ctx context.Context, req *pb.AddPlayerRequest) (*emptypb.Empty, error) {
	player, err := playerFromProto(req.GetPlayer())
	if err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "invalid player: %v", err)
	}

	switch req.GetQueue() {
	case pb.QueueType_QUEUE_TYPE_KILLER:
		addPlayerToPoolWithLock(KillerPool, &KillerPoolMutex, player)
	case pb.QueueType_QUEUE_TYPE_VICTIM:
		addPlayerToPoolWithLock(VictimPool, &VictimPoolMutex, player)
	default:
		return nil, status.Error(codes.InvalidArgument, "queue type must be killer or victim")
	}

	logger.Info("Player %d added to %s queue", player.TgId, req.GetQueue().String())
	return &emptypb.Empty{}, nil
}

func (s *matchmakingServer) AddPlayerToQueues(ctx context.Context, req *pb.AddPlayerToQueuesRequest) (*emptypb.Empty, error) {
	player, err := playerFromProto(req.GetPlayer())
	if err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "invalid player: %v", err)
	}

	addPlayerToPoolWithLock(KillerPool, &KillerPoolMutex, player)
	addPlayerToPoolWithLock(VictimPool, &VictimPoolMutex, player)
	logger.Info("Player %d added to both queues", player.TgId)
	return &emptypb.Empty{}, nil
}

func (s *matchmakingServer) GetQueuesLength(ctx context.Context, _ *emptypb.Empty) (*pb.GetQueuesLengthResponse, error) {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()
	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	return &pb.GetQueuesLengthResponse{
		Killers: int32(len(KillerPool)),
		Victims: int32(len(VictimPool)),
	}, nil
}

func (s *matchmakingServer) GetPlayer(ctx context.Context, req *pb.GetPlayerRequest) (*pb.GetPlayerResponse, error) {
	KillerPoolMutex.Lock()
	defer KillerPoolMutex.Unlock()
	VictimPoolMutex.Lock()
	defer VictimPoolMutex.Unlock()

	killer, queuedKiller := KillerPool[req.GetTgId()]
	victim, queuedVictim := VictimPool[req.GetTgId()]

	return &pb.GetPlayerResponse{
		QueuedKiller: queuedKiller,
		Killer:       playerToProto(killer),
		QueuedVictim: queuedVictim,
		Victim:       playerToProto(victim),
	}, nil
}

func (s *matchmakingServer) ResetQueues(ctx context.Context, _ *emptypb.Empty) (*emptypb.Empty, error) {
	logger.Info("ResetQueues request received")

	timeoutCtx, cancel := context.WithTimeout(ctx, conf.ReloadTimeout)
	defer cancel()

	cleanQueues()
	if err := populateQueues(timeoutCtx); err != nil {
		logger.Error("Failed to repopulate queues: %v", err)
		return nil, status.Errorf(codes.Internal, "failed to reload queues: %v", err)
	}

	logger.Info("Queues successfully reloaded")
	return &emptypb.Empty{}, nil
}

func addPlayerToPool(pool map[uint64]QueuePlayer, data PlayerData) {
	pool[data.TgId] = QueuePlayer{
		TgId:       data.TgId,
		JoinedAt:   time.Now(),
		PlayerData: data,
	}
}

func addPlayerToPoolWithLock(pool map[uint64]QueuePlayer, mu *sync.Mutex, data PlayerData) {
	mu.Lock()
	defer mu.Unlock()
	addPlayerToPool(pool, data)
}

func playerFromProto(msg *pb.PlayerData) (PlayerData, error) {
	if msg == nil {
		return PlayerData{}, fmt.Errorf("player is nil")
	}

	var courseNumber *int
	if msg.CourseNumber != nil {
		v := int(msg.GetCourseNumber())
		courseNumber = &v
	}

	player := PlayerData{
		TgId:         msg.GetTgId(),
		Rating:       int(msg.GetRating()),
		Type:         EducationTypeFromString(msg.GetType()),
		CourseNumber: courseNumber,
		GroupName:    GroupNameFromString(msg.GetGroupName()),
	}

	return *player.WithDefaultRating(), player.Validate()
}

func playerToProto(player QueuePlayer) *pb.PlayerData {
	var courseNumber *int32
	if player.CourseNumber != nil {
		v := int32(*player.CourseNumber)
		courseNumber = &v
	}

	return &pb.PlayerData{
		TgId:         player.TgId,
		Rating:       int32(player.Rating),
		Type:         player.Type.String(),
		CourseNumber: courseNumber,
		GroupName:    player.GroupName.String(),
	}
}
